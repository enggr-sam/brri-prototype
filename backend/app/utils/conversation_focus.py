"""Derive a stable troubleshooting focus from the whole conversation.

Follow-ups like “ছবি নাই?”, “show the picture”, “price kemon?” are short and
must inherit the last real machine topic — not only the previous short message.
"""

from __future__ import annotations

import re

_PHOTO_ASK = (
    "ছবি",
    "photo",
    "picture",
    "image",
    "দেখান",
    "দেখিয়",
    "দেখাই",
    "বুঝিয়",
    "বুঝাই",
    "visual",
    "diagram",
    "drawing",
    "blueprint",
    "cad",
    "নকশা",
    "ড্রয়িং",
    "show",
    "chobi",
    "chobi nai",
)

_SHORT_FOLLOWUP = (
    "কেন",
    "keno",
    "কী",
    "ki",
    "হ্যাঁ",
    "না",
    "আরও",
    "again",
    "ok",
    "ঠিক",
    "এভাবে",
    "কিভাবে",
    "কিভাবে",
    "kivabe",
)


_SHOWN_IMAGE_ASK = (
    "eta ki",
    "eita ki",
    "ei ta ki",
    "ita ki",
    "image e je",
    "image e ja",
    "je dilen",
    "je dile",
    "je dila",
    "je dilo",
    "chobi ta",
    "chobita",
    "ei chobi",
    "ei image",
    "that image",
    "this image",
    "what is this",
    "what's this",
    "what is that",
    "which part",
    "kon part",
    "ki part",
    "ছবিটা",
    "ছবিতে",
    "এই ছবি",
    "কী ছবি",
    "কি ছবি",
    "কোন অংশ",
)


def asks_for_photos(text: str) -> bool:
    lower = (text or "").lower()
    return any(m in lower for m in _PHOTO_ASK)


def is_asking_about_shown_image(text: str, history: list[dict] | None = None) -> bool:
    """True when the farmer asks what the last gallery photo was."""
    raw = (text or "").strip()
    if not raw or len(raw) > 90:
        return False
    lower = raw.lower()
    if any(p in lower or p in raw for p in _SHOWN_IMAGE_ASK):
        return True
    gallery = last_shown_gallery(history)
    if gallery and len(raw) <= 36 and any(
        q in lower or q in raw for q in ("ki", "কি", "কী", "what", "eta", "eita", "এটা")
    ):
        return True
    if asks_for_photos(raw) and any(
        q in lower or q in raw for q in ("কি", "কী", "ki ", " ki", "what")
    ):
        if any(s in lower or s in raw for s in ("দেখান", "show", "আরও", "nai", "নাই")):
            return False
        return True
    return False


def last_shown_gallery(history: list[dict] | None) -> list[dict]:
    for msg in reversed(history or []):
        if msg.get("role") != "assistant":
            continue
        gallery = msg.get("gallery") or []
        if gallery:
            return gallery
    return []


def _is_substantive(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 12:
        return False
    if asks_for_photos(t) and len(t) < 40:
        return False
    # Pure short confirmations
    if len(t) < 25 and any(t.lower().startswith(s) for s in _SHORT_FOLLOWUP):
        return False
    return True


def recent_substantive_user_texts(
    history: list[dict[str, str]] | None,
    *,
    limit: int = 3,
) -> list[str]:
    found: list[str] = []
    for msg in reversed(history or []):
        if msg.get("role") != "user":
            continue
        content = (msg.get("content") or "").strip()
        if not _is_substantive(content):
            continue
        found.append(content)
        if len(found) >= limit:
            break
    return list(reversed(found))


def last_assistant_snippet(
    history: list[dict[str, str]] | None,
    *,
    max_chars: int = 280,
) -> str:
    for msg in reversed(history or []):
        if msg.get("role") != "assistant":
            continue
        content = (msg.get("content") or "").strip()
        if content:
            return content[:max_chars]
    return ""


def build_conversation_focus(
    user_text: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    """Single search string that captures the farmer's real topic."""
    current = (user_text or "").strip()
    prior = recent_substantive_user_texts(history, limit=3)
    parts: list[str] = []

    inherit = asks_for_photos(current) or len(current) < 45 or not _is_substantive(current)

    if inherit and prior:
        parts.extend(prior)
        asst = last_assistant_snippet(history)
        if asst:
            # Keep symptom/solution keywords for retrieval continuity.
            parts.append(asst)
    elif prior and len(current) < 80:
        # Short new turn may still refer to the open topic.
        parts.append(prior[-1])

    if current:
        parts.append(current)

    focus = " ".join(p for p in parts if p).strip()
    focus = re.sub(r"\s+", " ", focus)
    return focus


def conversation_wants_visuals(
    user_text: str,
    history: list[dict[str, str]] | None = None,
) -> bool:
    if asks_for_photos(user_text or ""):
        return True
    # Explicit photo ask earlier in the same open topic.
    for msg in reversed((history or [])[-4:]):
        if msg.get("role") == "user" and asks_for_photos(msg.get("content") or ""):
            return True
    return False
