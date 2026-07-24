"""Interactive chat API + reference image / attachment serving."""

import logging
import uuid
from pathlib import Path
from typing import NoReturn

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import ChatMessage, ChatSession
from app.schemas import ChatHistoryOut, ChatMessageOut, ChatResponse, ReferenceImageOut
from app.services.gemini_service import QuotaExceededError, gemini_service
from app.services.knowledge_base import get_knowledge_base
from app.services.reference_selector import select_reference_images
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


def _message_out(msg: ChatMessage) -> ChatMessageOut:
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
        created_at=msg.created_at,
    )


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


@router.post("/chat/message", response_model=ChatResponse)
async def chat_message(
    session_id: str | None = Form(default=None),
    text: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    audio: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> ChatResponse:
    """Send a chat message (text, image, and/or voice) and get a Bengali reply."""
    get_knowledge_base()

    if not text and not image and not audio:
        raise HTTPException(status_code=400, detail="Send text, an image, or audio.")

    # --- Session ---------------------------------------------------------
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

    # --- User input processing -------------------------------------------
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

    # --- Gemini ----------------------------------------------------------
    reference_paths = select_reference_images(user_text=user_content)

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

    answer = chat_result.text
    ref_meta = reference_images_metadata(reference_paths, captions=chat_result.image_captions)

    # --- Persist ---------------------------------------------------------
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=user_content,
        modality=modality,
        attachment_path=attachment_path,
    )
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
        modality="text",
        reference_images_json=dumps_reference_images(ref_meta),
    )
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)

    assistant_out = _message_out(assistant_msg)
    # Ensure gallery is populated even if JSON round-trip differs.
    if not assistant_out.reference_images and ref_meta:
        assistant_out = assistant_out.model_copy(
            update={"reference_images": [ReferenceImageOut(**m) for m in ref_meta]}
        )

    return ChatResponse(
        session_id=session.id,
        user_message=_message_out(user_msg),
        assistant_message=assistant_out,
    )


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
    )
