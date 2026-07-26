"""Canonical Bangla replies when the model output is empty, truncated, or leaked meta."""

from __future__ import annotations

import re

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
    if is_chaff_issue_query(user_text):
        return format_chaff_wind_reply_bn()
    if cleaned:
        return cleaned
    return "দুঃখিত, উত্তর তৈরি করা যায়নি। অনুগ্রহ করে আবার প্রশ্ন করুন।"
