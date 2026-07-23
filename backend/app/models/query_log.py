"""``QueryLog`` model: an audit record for every troubleshooting request."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class QueryLog(Base):
    """Persists each user interaction with the troubleshooting assistant.

    We store the modality (``vision`` or ``voice``), any uploaded file paths,
    the user's text, the transcription (for audio), and the LLM's response so
    the full exchange is auditable and reviewable later.
    """

    __tablename__ = "query_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # "vision" or "voice"
    modality: Mapped[str] = mapped_column(String(20), nullable=False)

    # Relative paths to the stored user uploads (nullable per modality).
    image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    audio_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Optional free-text the user typed alongside the upload.
    user_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Transcription produced from the audio (voice modality only).
    transcription: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The Bengali troubleshooting answer returned by Gemini.
    response: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<QueryLog id={self.id} modality={self.modality!r} at={self.created_at}>"
