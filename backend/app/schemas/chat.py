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
    follow_up_suggestions: list[str] = []
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    model_used: str | None = None
    created_at: datetime


class ChatResponse(BaseModel):
    session_id: str
    user_message: ChatMessageOut
    assistant_message: ChatMessageOut
    session_total_cost_usd: float = 0.0


class ChatHistoryOut(BaseModel):
    session_id: str
    messages: list[ChatMessageOut]
    session_total_cost_usd: float = 0.0


class ChatSessionSummaryOut(BaseModel):
    session_id: str
    started_at: datetime
    last_message_at: datetime
    message_count: int
    preview: str


class ChatSessionsListOut(BaseModel):
    total: int
    sessions: list[ChatSessionSummaryOut]
