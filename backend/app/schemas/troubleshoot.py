"""Pydantic schemas for the troubleshooting endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TroubleshootResponse(BaseModel):
    """Response returned by the vision and voice endpoints."""

    id: int
    modality: str
    response: str
    transcription: str | None = None
    reference_images_used: list[str] = []
    created_at: datetime


class QueryLogOut(BaseModel):
    """Serialised ``QueryLog`` row, used by the history endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    modality: str
    image_path: str | None = None
    audio_path: str | None = None
    user_text: str | None = None
    transcription: str | None = None
    response: str | None = None
    created_at: datetime
