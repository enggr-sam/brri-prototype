"""Build API metadata for reference images used in a response."""

import json
from pathlib import Path

from app.services.knowledge_base import get_knowledge_base


def _short_label(image_name: str) -> str:
    """Human-readable label from filename (strip number prefix and extension)."""
    name = image_name
    if "_" in name and name[:2].isdigit():
        name = name.split("_", 1)[1]
    return name.rsplit(".", 1)[0].replace("_", " ").title()


def reference_images_metadata(
    paths: list[Path],
    captions: dict[int, str] | None = None,
) -> list[dict]:
    """Return serialisable metadata for each reference image (for the UI gallery)."""
    kb = get_knowledge_base()
    items: list[dict] = []
    for path in paths:
        entry = kb._by_name.get(path.name, {})
        desc = entry.get("description") or ""
        image_number = entry.get("image_number")
        contextual_note = None
        if captions and image_number is not None:
            contextual_note = captions.get(image_number)
        items.append(
            {
                "image_number": image_number,
                "image_name": path.name,
                "url": f"/api/reference-images/{path.name}",
                "label": _short_label(path.name),
                "description": desc,
                "contextual_note": contextual_note,
            }
        )
    return items


def dumps_reference_images(metadata: list[dict]) -> str:
    return json.dumps(metadata, ensure_ascii=False)


def loads_reference_images(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []
