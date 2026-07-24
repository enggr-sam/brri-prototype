"""Pydantic schemas for the chat API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReferenceImageOut(BaseModel):
    image_number: int | None = None
    image_name: str
    url: str
    label: str
    description: str | None = None
    contextual_note: str | None = None


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    modality: str
    attachment_url: str | None = None
    reference_images: list[ReferenceImageOut] = []
    created_at: datetime


class ChatResponse(BaseModel):
    session_id: str
    user_message: ChatMessageOut
    assistant_message: ChatMessageOut


class ChatHistoryOut(BaseModel):
    session_id: str
    messages: list[ChatMessageOut]
