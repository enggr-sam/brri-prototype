"""Troubleshooting API routes (vision + voice) and query history."""

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import QueryLog
from app.schemas import QueryLogOut, TroubleshootResponse
from app.services.gemini_service import gemini_service
from app.utils.files import (
    AUDIO_CONTENT_TYPES,
    IMAGE_CONTENT_TYPES,
    read_reference_images,
    relative_to_backend,
    save_upload,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/troubleshoot", tags=["troubleshoot"])

# Cap how many reference images we attach to keep requests fast/cheap.
MAX_REFERENCE_IMAGES = 4


@router.post("/vision", response_model=TroubleshootResponse)
async def troubleshoot_vision(
    image: UploadFile = File(..., description="Photo of the (possibly broken) part"),
    text: str | None = Form(default=None, description="Optional description"),
    db: Session = Depends(get_db),
) -> TroubleshootResponse:
    """Analyse an uploaded image (plus optional text) and return a Bengali fix."""
    if image.content_type not in IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image type: {image.content_type}",
        )

    image_path = await save_upload(image, subdir="images", fallback_ext=".jpg")
    reference_images = read_reference_images(limit=MAX_REFERENCE_IMAGES)

    try:
        answer = gemini_service.analyze_image(
            image_path=image_path,
            user_text=text,
            reference_images=reference_images,
        )
    except Exception as exc:
        logger.exception("Vision troubleshooting failed.")
        raise HTTPException(status_code=502, detail="AI service error.") from exc

    log = QueryLog(
        modality="vision",
        image_path=relative_to_backend(image_path),
        user_text=text,
        response=answer,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return TroubleshootResponse(
        id=log.id,
        modality=log.modality,
        response=answer,
        reference_images_used=[p.name for p in reference_images],
        created_at=log.created_at,
    )


@router.post("/voice", response_model=TroubleshootResponse)
async def troubleshoot_voice(
    audio: UploadFile = File(..., description="Voice recording describing the issue"),
    db: Session = Depends(get_db),
) -> TroubleshootResponse:
    """Transcribe an uploaded audio clip and return a Bengali troubleshooting fix."""
    if audio.content_type not in AUDIO_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio type: {audio.content_type}",
        )

    audio_path = await save_upload(audio, subdir="audio", fallback_ext=".webm")
    reference_images = read_reference_images(limit=MAX_REFERENCE_IMAGES)

    try:
        transcription = gemini_service.transcribe_audio(audio_path)
        answer = gemini_service.analyze_voice(
            audio_path=audio_path,
            transcription=transcription,
            reference_images=reference_images,
        )
    except Exception as exc:
        logger.exception("Voice troubleshooting failed.")
        raise HTTPException(status_code=502, detail="AI service error.") from exc

    log = QueryLog(
        modality="voice",
        audio_path=relative_to_backend(audio_path),
        transcription=transcription,
        response=answer,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return TroubleshootResponse(
        id=log.id,
        modality=log.modality,
        response=answer,
        transcription=transcription or None,
        reference_images_used=[p.name for p in reference_images],
        created_at=log.created_at,
    )


@router.get("/history", response_model=list[QueryLogOut])
def troubleshoot_history(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[QueryLog]:
    """Return the most recent query logs (newest first)."""
    stmt = select(QueryLog).order_by(QueryLog.created_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())
