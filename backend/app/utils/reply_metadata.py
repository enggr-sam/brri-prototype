"""Parse hidden metadata block (suggestions, image flag) from model replies."""

from __future__ import annotations

import json
import re

META_MARKER = "---META---"


def split_reply_metadata(text: str) -> tuple[str, dict]:
    """Split visible reply from trailing metadata block."""
    if META_MARKER not in text:
        return text.strip(), {}

    main, tail = text.split(META_MARKER, 1)
    meta: dict = {"suggestions": [], "show_images": True}

    tail = tail.strip()
    if not tail:
        return main.strip(), meta

    # Try JSON first: {"suggestions":[...],"show_images":false}
    json_match = re.search(r"\{.*\}", tail, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
            if isinstance(parsed.get("suggestions"), list):
                meta["suggestions"] = [
                    str(s).strip() for s in parsed["suggestions"] if str(s).strip()
                ][:3]
            if "show_images" in parsed:
                meta["show_images"] = bool(parsed["show_images"])
            return main.strip(), meta
        except json.JSONDecodeError:
            pass

    for line in tail.splitlines():
        line = line.strip()
        if line.upper().startswith("SUGGEST:"):
            raw = line.split(":", 1)[1]
            parts = re.split(r"\||\n", raw)
            meta["suggestions"] = [p.strip() for p in parts if p.strip()][:3]
        elif line.upper().startswith("IMAGES:"):
            val = line.split(":", 1)[1].strip().lower()
            meta["show_images"] = val in ("yes", "true", "1")

    return main.strip(), meta


def dumps_suggestions(items: list[str]) -> str | None:
    cleaned = [s.strip() for s in items if s and s.strip()]
    if not cleaned:
        return None
    return json.dumps(cleaned[:3], ensure_ascii=False)


def loads_suggestions(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return [str(s) for s in data][:3] if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []
