"""Canonical Bangla replies when the model output is empty, truncated, or leaked meta."""

from __future__ import annotations

import re

from app.services.knowledge_base import get_knowledge_base
from app.utils.reply_metadata import strip_leaked_metadata

_CHAFF_TERMS = (
    "chita",
    "chaff",
    "চিট",
    "চিটা",
    "তুষ",
    "ure jai",
    "ure jay",
    "uRe jai",
    "flying",
    "উড়",
    "উড়",
    "ভেসে",
    "বাতাস বেশি",
    "too much wind",
    "keno eto",
    "এত বেশি",
)


def is_chaff_issue_query(text: str) -> bool:
    lower = (text or "").lower()
    return any(term in lower for term in _CHAFF_TERMS)


# A refusal is phrased freely by the model, so match on the scope statement plus a
# decline. Both are required: "সাহায্য করতে পারি" alone appears in real answers too.
_REFUSAL_SCOPE_MARKERS = ("শুধুমাত্র", "কেবল", "শুধু ")
_REFUSAL_DECLINE_MARKERS = (
    "সাহায্য করতে পারি",
    "দিতে পারব না",
    "দিতে পারি না",
    "উত্তর দিতে পারব না",
    "বলতে পারব না",
    "আমার আওতার বাইরে",
)


def is_off_topic_refusal(reply: str) -> bool:
    """True when the reply declines an off-topic question.

    Machine photos under a "I only help with this winnower" answer look like a bug to
    the farmer, so the gallery is suppressed for these turns.
    """
    text = (reply or "").strip()
    if not text or len(text) > 600:
        return False
    return any(m in text for m in _REFUSAL_SCOPE_MARKERS) and any(
        m in text for m in _REFUSAL_DECLINE_MARKERS
    )


def format_chaff_wind_reply_bn() -> str:
    return (
        "সমস্যা: ব্লোয়ারের বাতাস বেশি থাকলে চিটা/তুষ বেশি উড়ে যায়; "
        "বাতাস অতিরিক্ত হলে ভালো ধানও উড়তে পারে।\n\n"
        "সমাধান:\n"
        "১. ব্লোয়ারের বাতাস নিয়ন্ত্রণ লিভার বা এয়ার কন্ট্রোল প্লেট একটু বন্ধ "
        "করে বাতাসের পরিমাণ কমান।\n"
        "২. হপারের সবুজ ফিড গেট সামান্য সামঞ্জস্য করে ধানের প্রবাহ ঠিক রাখুন।\n\n"
        "সাবধান: বাতাস একবারে খুব বেশি কমালে চিটা/ময়লা আলাদা হবে না — "
        "অল্প অল্প করে কমিয়ে দেখুন।"
    )


def _tokenize(text: str) -> set[str]:
    return {t for t in re.split(r"[^\w\u0980-\u09FF]+", text.lower()) if len(t) >= 2}


def match_field_fault(user_text: str) -> dict | None:
    """Return the best-matching field-collected fault entry, if any."""
    kb = get_knowledge_base()
    if not kb.fault_trees:
        return None

    ql = (user_text or "").lower()
    tokens = _tokenize(ql)
    best: dict | None = None
    best_score = 0.0

    for ft in kb.fault_trees:
        score = 0.0
        for kw in ft.get("keywords") or []:
            if kw and kw in ql:
                score += 3.0
        symptom = (ft.get("symptom_local_bn") or "").lower()
        part = (ft.get("part_local_bn") or "").lower()
        for token in tokens:
            if token in symptom:
                score += 2.5
            if token in part:
                score += 1.5
        if score > best_score:
            best_score = score
            best = ft

    return best if best_score >= 4.0 else None


def format_field_fault_reply_bn(fault: dict) -> str:
    symptom = fault.get("symptom_local_bn") or fault.get("symptom_paper") or "সমস্যা"
    solution = (fault.get("solution_bn") or "").strip()
    part = fault.get("part_paper") or ""
    lines = [f"সমস্যা: {symptom}"]
    if part:
        lines[0] += f" ({part})"
    if solution:
        lines += ["", "সমাধান:", solution]
    photo_nums = fault.get("photo_numbers") or []
    if photo_nums:
        lines += ["", f"সংশ্লিষ্ট ছবি নং: {', '.join(photo_nums)}"]
    return "\n".join(lines)


def _reply_is_usable(text: str) -> bool:
    t = strip_leaked_metadata(text).strip()
    if len(t) < 25:
        return False
    lower = t.lower()
    if re.match(r"^:\s*true\b", t, re.IGNORECASE):
        return False
    if "suggestions" in lower and "follow-up" in lower and len(t) < 120:
        return False
    if re.search(r"[\u0980-\u09FF]", t):
        return True
    if t.startswith("সমস্যা:"):
        return True
    return len(t) >= 80 and "সমাধান" in t


def ensure_canonical_reply(text: str, user_text: str) -> str:
    """Replace garbage / empty model output with a known-good answer."""
    cleaned = strip_leaked_metadata(text).strip()
    if _reply_is_usable(cleaned):
        return cleaned

    field_fault = match_field_fault(user_text)
    if field_fault:
        return format_field_fault_reply_bn(field_fault)

    if is_chaff_issue_query(user_text):
        return format_chaff_wind_reply_bn()
    if cleaned:
        return cleaned
    return "দুঃখিত, উত্তর তৈরি করা যায়নি। অনুগ্রহ করে আবার প্রশ্ন করুন।"
