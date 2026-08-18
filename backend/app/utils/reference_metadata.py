"""Build API metadata for reference images used in a response."""

import json
from pathlib import Path

from app.services.knowledge_base import get_knowledge_base
from app.utils.image_labels import display_label


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
                "label": display_label(entry, path.name),
                "description": desc,
                "contextual_note": contextual_note,
                "drive_folder_url": entry.get("drive_folder_url"),
                "source": entry.get("source"),
                "photo_no": entry.get("photo_no"),
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
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    # Labels are recomputed on read so older messages, saved when captions came from
    # filenames, show the current Bangla wording too.
    kb = get_knowledge_base()
    for item in data:
        name = item.get("image_name")
        if name:
            item["label"] = display_label(kb._by_name.get(name, {}), name)
    return data
