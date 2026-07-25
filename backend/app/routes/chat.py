"""Interactive chat API + reference image / attachment serving."""

import json
import logging
import uuid
from pathlib import Path
from typing import Any, NoReturn

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, get_db
from app.models import ChatMessage, ChatSession
from app.schemas import (
    ChatHistoryOut,
    ChatMessageOut,
    ChatResponse,
    ChatSessionSummaryOut,
    ChatSessionsListOut,
    ReferenceImageOut,
)
from app.services.gemini_service import ChatReplyResult, QuotaExceededError, gemini_service
from app.services.knowledge_base import get_knowledge_base
from app.services.reference_selector import (
    order_reference_images_by_relevance,
    select_reference_images,
)
from app.utils.files import (
    AUDIO_CONTENT_TYPES,
    IMAGE_CONTENT_TYPES,
    relative_to_backend,
    save_upload,
)
from app.utils.reference_metadata import (
    dumps_reference_images,
    loads_reference_images,
    reference_images_metadata,
)
from app.utils.reply_metadata import dumps_suggestions, loads_suggestions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

_QUOTA_MESSAGE_BN = (
    "দুঃখিত, AI সেবার অনুরোধ সীমা (quota) শেষ হয়ে গেছে। "
    "অনুগ্রহ করে কিছুক্ষণ পর আবার চেষ্টা করুন।"
)


def _raise_quota(exc: QuotaExceededError) -> NoReturn:
    headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
    raise HTTPException(status_code=429, detail=_QUOTA_MESSAGE_BN, headers=headers)


def _safe_filename(name: str) -> bool:
    return ".." not in name and "/" not in name and "\\" not in name


def _message_out(msg: ChatMessage, session_total: float | None = None) -> ChatMessageOut:
    attachment_url = None
    if msg.attachment_path and msg.role == "user":
        attachment_url = f"/api/attachments/{msg.attachment_path}"
    return ChatMessageOut(
        id=msg.id,
        role=msg.role,
        content=msg.content,
        modality=msg.modality,
        attachment_url=attachment_url,
        reference_images=[
            ReferenceImageOut(**item) for item in loads_reference_images(msg.reference_images_json)
        ],
        follow_up_suggestions=loads_suggestions(msg.follow_up_suggestions_json),
        cost_usd=float(msg.cost_usd or 0.0),
        input_tokens=int(msg.input_tokens or 0),
        output_tokens=int(msg.output_tokens or 0),
        model_used=msg.model_used,
        created_at=msg.created_at,
    )


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _should_attach_reference_images(user_text: str, has_user_image: bool) -> bool:
    if has_user_image:
        return True
    text = user_text.lower()
    basic_markers = (
        "ratio", "ration", "অনুপাত", "spec", "স্পেস", "সাইজ", "size", "কত",
        "dimension", "bom", "what is", "কী সাইজ", "মডেল",
    )
    if any(m in text for m in basic_markers) and len(text) < 100:
        return False
    return True


async def _prepare_user_input(
    text: str | None,
    image: UploadFile | None,
    audio: UploadFile | None,
) -> tuple[str, str, str | None, Path | None]:
    user_content = (text or "").strip()
    modality = "text"
    attachment_path: str | None = None
    user_image_path: Path | None = None

    if audio is not None:
        audio_type = (audio.content_type or "").split(";")[0].strip().lower()
        if audio_type not in AUDIO_CONTENT_TYPES:
            raise HTTPException(status_code=415, detail=f"Unsupported audio: {audio.content_type}")
        audio_path = await save_upload(audio, subdir="audio", fallback_ext=".webm")
        attachment_path = relative_to_backend(audio_path)
        modality = "voice"
        try:
            transcription = gemini_service.transcribe_audio(
                audio_path, content_type=audio.content_type
            )
        except QuotaExceededError as exc:
            _raise_quota(exc)
        user_content = transcription.strip() or user_content or "(voice message)"

    if image is not None:
        if image.content_type not in IMAGE_CONTENT_TYPES:
            raise HTTPException(status_code=415, detail=f"Unsupported image: {image.content_type}")
        image_path = await save_upload(image, subdir="images", fallback_ext=".jpg")
        user_image_path = image_path
        attachment_path = relative_to_backend(image_path)
        modality = "vision" if modality != "voice" else "vision"

    if not user_content:
        user_content = "এই যন্ত্রাংশে কী সমস্যা হতে পারে?" if user_image_path else "সাহায্য করুন।"

    return user_content, modality, attachment_path, user_image_path


def _save_turn(
    db: Session,
    session_id: str,
    user_content: str,
    modality: str,
    attachment_path: str | None,
    chat_result: ChatReplyResult,
    reference_paths: list[Path],
) -> tuple[ChatMessage, ChatMessage, float]:
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    if chat_result.show_reference_images and reference_paths:
        reference_paths = order_reference_images_by_relevance(
            reference_paths,
            f"{user_content}\n{chat_result.text}",
        )
        ref_meta = reference_images_metadata(reference_paths, captions=chat_result.image_captions)
    else:
        ref_meta = []

    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=user_content,
        modality=modality,
        attachment_path=attachment_path,
    )
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=chat_result.text,
        modality="text",
        reference_images_json=dumps_reference_images(ref_meta) if ref_meta else None,
        follow_up_suggestions_json=dumps_suggestions(chat_result.suggestions),
        cost_usd=chat_result.usage.cost_usd,
        input_tokens=chat_result.usage.input_tokens,
        output_tokens=chat_result.usage.output_tokens,
        model_used=chat_result.usage.model_used,
    )
    session.total_cost_usd = round(
        float(session.total_cost_usd or 0.0) + chat_result.usage.cost_usd, 6
    )

    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)
    return user_msg, assistant_msg, float(session.total_cost_usd or 0.0)


@router.get("/reference-images/{filename}")
def serve_reference_image(filename: str) -> FileResponse:
    """Serve intact-part reference photos for the UI gallery."""
    if not _safe_filename(filename):
        raise HTTPException(status_code=400, detail="Invalid filename.")
    path = settings.reference_images_dir / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found.")
    return FileResponse(path)


@router.get("/attachments/{path:path}")
def serve_attachment(path: str) -> FileResponse:
    """Serve user uploads (images/audio) from the uploads directory."""
    if ".." in path:
        raise HTTPException(status_code=400, detail="Invalid path.")
    full = (settings.UPLOAD_DIR.parent / path).resolve()
    uploads_root = settings.UPLOAD_DIR.resolve()
    if not str(full).startswith(str(uploads_root.parent)):
        raise HTTPException(status_code=403, detail="Forbidden.")
    if not full.is_file():
        raise HTTPException(status_code=404, detail="Attachment not found.")
    return FileResponse(full)


@router.post("/chat/message/stream")
async def chat_message_stream(
    session_id: str | None = Form(default=None),
    text: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    audio: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Stream assistant reply tokens (SSE), then persist with cost + suggestions."""
    get_knowledge_base()

    if not text and not image and not audio:
        raise HTTPException(status_code=400, detail="Send text, an image, or audio.")

    if session_id:
        session = db.get(ChatSession, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")
    else:
        session = ChatSession(id=str(uuid.uuid4()))
        db.add(session)
        db.commit()
        db.refresh(session)

    session_id_str = session.id

    history_rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id_str)
        .order_by(ChatMessage.created_at)
    ).all()
    history = [{"role": m.role, "content": m.content} for m in history_rows]

    user_content, modality, attachment_path, user_image_path = await _prepare_user_input(
        text, image, audio
    )

    reference_paths: list[Path] = []
    if _should_attach_reference_images(user_content, user_image_path is not None):
        reference_paths = select_reference_images(
            user_text=user_content,
            has_user_image=user_image_path is not None,
        )

    def event_stream():
        try:
            yield _sse({"type": "start", "session_id": session_id_str})

            for token in gemini_service.stream_visible_tokens(
                history=history,
                user_text=user_content,
                reference_images=reference_paths,
                user_image_path=user_image_path,
            ):
                yield _sse({"type": "token", "text": token})

            chat_result = gemini_service.finalize_streamed_reply(
                user_content, reference_paths
            )
            save_db = SessionLocal()
            try:
                user_msg, assistant_msg, session_total = _save_turn(
                    save_db,
                    session_id_str,
                    user_content,
                    modality,
                    attachment_path,
                    chat_result,
                    reference_paths,
                )
            finally:
                save_db.close()

            assistant_out = _message_out(assistant_msg)
            user_out = _message_out(user_msg)

            yield _sse(
                {
                    "type": "done",
                    "session_id": session_id_str,
                    "session_total_cost_usd": session_total,
                    "user_message": user_out.model_dump(mode="json"),
                    "assistant_message": assistant_out.model_dump(mode="json"),
                }
            )
        except QuotaExceededError as exc:
            yield _sse({"type": "error", "detail": _QUOTA_MESSAGE_BN, "retry_after": exc.retry_after})
        except Exception:
            logger.exception("Streaming chat failed.")
            yield _sse({"type": "error", "detail": "AI service error."})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat/message", response_model=ChatResponse)
async def chat_message(
    session_id: str | None = Form(default=None),
    text: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    audio: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> ChatResponse:
    """Non-streaming fallback — same logic as /chat/message/stream."""
    get_knowledge_base()

    if not text and not image and not audio:
        raise HTTPException(status_code=400, detail="Send text, an image, or audio.")

    if session_id:
        session = db.get(ChatSession, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")
    else:
        session = ChatSession(id=str(uuid.uuid4()))
        db.add(session)
        db.flush()

    history_rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
    ).all()
    history = [{"role": m.role, "content": m.content} for m in history_rows]

    user_content, modality, attachment_path, user_image_path = await _prepare_user_input(
        text, image, audio
    )

    reference_paths: list[Path] = []
    if _should_attach_reference_images(user_content, user_image_path is not None):
        reference_paths = select_reference_images(
            user_text=user_content,
            has_user_image=user_image_path is not None,
        )

    try:
        chat_result = gemini_service.chat_reply(
            history=history,
            user_text=user_content,
            reference_images=reference_paths,
            user_image_path=user_image_path,
        )
    except QuotaExceededError as exc:
        _raise_quota(exc)
    except Exception as exc:
        logger.exception("Chat message failed.")
        raise HTTPException(status_code=502, detail="AI service error.") from exc

    user_msg, assistant_msg, session_total = _save_turn(
        db,
        session.id,
        user_content,
        modality,
        attachment_path,
        chat_result,
        reference_paths,
    )

    assistant_out = _message_out(assistant_msg)
    if not assistant_out.reference_images and chat_result.show_reference_images:
        ref_meta = reference_images_metadata(
            order_reference_images_by_relevance(reference_paths, f"{user_content}\n{chat_result.text}"),
            captions=chat_result.image_captions,
        )
        if ref_meta:
            assistant_out = assistant_out.model_copy(
                update={"reference_images": [ReferenceImageOut(**m) for m in ref_meta]}
            )

    return ChatResponse(
        session_id=session.id,
        user_message=_message_out(user_msg),
        assistant_message=assistant_out,
        session_total_cost_usd=session_total,
    )


@router.get("/chat/sessions/list", response_model=ChatSessionsListOut)
def list_chat_sessions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ChatSessionsListOut:
    """List all chat sessions (newest activity first) with a short preview."""
    total = db.scalar(select(func.count()).select_from(ChatSession)) or 0

    rows = db.execute(
        select(
            ChatSession.id,
            ChatSession.created_at,
            func.count(ChatMessage.id).label("message_count"),
            func.max(ChatMessage.created_at).label("last_message_at"),
        )
        .join(ChatMessage, ChatMessage.session_id == ChatSession.id)
        .group_by(ChatSession.id)
        .order_by(func.max(ChatMessage.created_at).desc())
        .offset(offset)
        .limit(limit)
    ).all()

    summaries: list[ChatSessionSummaryOut] = []
    for row in rows:
        first_user = db.scalar(
            select(ChatMessage.content)
            .where(
                ChatMessage.session_id == row.id,
                ChatMessage.role == "user",
            )
            .order_by(ChatMessage.created_at)
            .limit(1)
        )
        preview = (first_user or "").strip()
        if len(preview) > 140:
            preview = preview[:140].rstrip() + "…"

        summaries.append(
            ChatSessionSummaryOut(
                session_id=row.id,
                started_at=row.created_at,
                last_message_at=row.last_message_at,
                message_count=row.message_count,
                preview=preview or "(no text)",
            )
        )

    return ChatSessionsListOut(total=total, sessions=summaries)


@router.get("/chat/{session_id}", response_model=ChatHistoryOut)
def chat_history(session_id: str, db: Session = Depends(get_db)) -> ChatHistoryOut:
    """Return full message history for a session."""
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    messages = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    ).all()
    return ChatHistoryOut(
        session_id=session_id,
        messages=[_message_out(m) for m in messages],
        session_total_cost_usd=float(session.total_cost_usd or 0.0),
    )
