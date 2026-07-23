"""Filesystem helpers for saving uploads and reading reference media."""

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile

from app.config import settings

# Basic allow-lists so we don't persist arbitrary content types.
IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
}
AUDIO_CONTENT_TYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/m4a",
    "audio/aac",
}


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _timestamped_name(original: str | None, fallback_ext: str) -> str:
    """Build a collision-resistant filename preserving the extension."""
    ext = ""
    if original and "." in original:
        ext = "." + original.rsplit(".", 1)[-1].lower()
    if not ext:
        ext = fallback_ext
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{stamp}_{uuid.uuid4().hex[:8]}{ext}"


async def save_upload(upload: UploadFile, subdir: str, fallback_ext: str) -> Path:
    """Persist an ``UploadFile`` under ``uploads/<subdir>/`` and return its path.

    Reads the file in chunks so large uploads do not blow up memory.
    """
    target_dir = settings.UPLOAD_DIR / subdir
    _ensure_dir(target_dir)

    filename = _timestamped_name(upload.filename, fallback_ext)
    dest = target_dir / filename

    with dest.open("wb") as out:
        while chunk := await upload.read(1024 * 1024):  # 1 MB chunks
            out.write(chunk)
    await upload.seek(0)
    return dest


def relative_to_backend(path: Path) -> str:
    """Return a path relative to the backend dir for tidy DB storage."""
    try:
        return str(path.relative_to(settings.KNOWLEDGE_BASE_DIR.parent))
    except ValueError:
        return str(path)


def read_reference_images(limit: int | None = None) -> list[Path]:
    """Return image files inside ``knowledge_base/reference_images/``.

    These "healthy part" images are sent to Gemini alongside the user's photo
    so the model can compare the broken part against a known-good reference.
    """
    ref_dir = settings.reference_images_dir
    if not ref_dir.exists():
        return []

    valid_ext = {".jpg", ".jpeg", ".png", ".webp"}
    images = sorted(
        p for p in ref_dir.iterdir() if p.is_file() and p.suffix.lower() in valid_ext
    )
    return images[:limit] if limit else images
