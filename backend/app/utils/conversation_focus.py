"""Derive a stable troubleshooting focus from the whole conversation.

Follow-ups like “ছবি নাই?”, “show the picture”, “price kemon?” are short and
must inherit the last real machine topic — not only the previous short message.
"""

from __future__ import annotations

import re

_PHOTO_NOUNS = (
    "ছবি",
    "photo",
    "picture",
    "image",
    "visual",
    "diagram",
    "drawing",
    "blueprint",
    "cad",
    "নকশা",
    "ড্রয়িং",
    "chobi",
    "chobi nai",
)

_PHOTO_SHOW = (
    "দেখান",
    "দেখাও",
    "দেখাইয়া দাও",
    "show me",
    "show the",
    "show a",
    "show photo",
    "pic dao",
    "pic den",
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


_FULL_MACHINE = (
    "full body",
    "fullbody",
    "full machine",
    "whole machine",
    "whole body",
    "complete body",
    "pura body",
    "pura machine",
    "pura meshin",
    "full pic",
    "full chobi",
    "full photo",
    "পুরো বডি",
    "পুরা বডি",
    "পুরো মেশিন",
    "পুরা মেশিন",
    "পুরো ছবি",
    "পুরা ছবি",
    "machine er pura",
    "meshin er pura",
    "pura bodyr",
    "পুরা বডির",
    "পুরো বডির",
)


def asks_for_full_machine(text: str) -> bool:
    """True when they want a photo of the whole machine, not a part."""
    raw = text or ""
    lower = raw.lower()
    if any(m in lower or m in raw for m in _FULL_MACHINE):
        return True
    has_whole = any(w in lower or w in raw for w in ("full", "pura", "পুরো", "পুরা", "whole", "সমগ্র"))
    has_body = any(w in lower or w in raw for w in ("body", "বডি", "machine", "মেশিন", "meshin", "winnower"))
    has_photo = asks_for_photos(raw) or bool(re.search(r"(?<![a-z])pics?(?![a-z])", lower))
    return bool(has_whole and has_body and has_photo)


def asks_for_photos(text: str) -> bool:
    """True only for an explicit photo / drawing request — not 'what should I check'."""
    raw = text or ""
    lower = raw.lower()
    if any(m in lower or m in raw for m in _PHOTO_NOUNS):
        return True
    # "pic" as its own word (full body pic/) — not a substring of pick/typical.
    if re.search(r"(?<![a-z])pics?(?![a-z])", lower):
        return True
    if any(m in lower or m in raw for m in _PHOTO_SHOW):
        # "কী কী দেখতে হবে" is a checklist, not "show me a picture".
        if "দেখতে" in raw and "দেখান" not in raw and "দেখাও" not in raw:
            return False
        return True
    return False


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
    # Whole-machine photo is a new topic — do not keep the last part/symptom.
    if asks_for_full_machine(current):
        inherit = False

    if inherit and prior:
        parts.extend(prior)
        asst = last_assistant_snippet(history)
        if asst:
            # Keep symptom/solution keywords for retrieval continuity.
            parts.append(asst)
    elif prior and len(current) < 80 and not asks_for_full_machine(current):
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
    if asks_for_photos(user_text or "") or asks_for_full_machine(user_text or ""):
        return True
    current = (user_text or "").strip()
    # Short "that one too / again" after they already asked to see a photo.
    follow = ("আরও", "আরো", "again", "same", "ওইটা", "এটাও", "ওই")
    if len(current) < 28 and any(x in current.lower() or x in current for x in follow):
        for msg in reversed((history or [])[-4:]):
            if msg.get("role") == "user" and asks_for_photos(msg.get("content") or ""):
                return True
    return False
