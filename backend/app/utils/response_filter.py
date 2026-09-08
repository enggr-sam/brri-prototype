"""Light cleanup of assistant replies — remove noise, never cut mid-sentence."""

import re

from app.utils.bangla_text import nfc
from app.utils.reply_metadata import strip_leaked_metadata
from app.utils.machine_identity import strip_forbidden_names

_NOISE_PATTERNS = [
    r"^#{1,6}\s+.+$",
    r"^---+$",
    r"^উপসংহার.*",
    r"^সারসংক্ষেপ.*",
    r"^আমি\s+(একজন\s+)?AI.*",
    r"^As an AI.*",
    r"^I am an AI.*",
    r"^Note:.*",
    r"^Disclaimer:.*",
]


# Sentences that point at the gallery ("ছবি নিচে দেখানো হয়েছে")। Harmless when the
# gallery is there, confusing when it is not.
_GALLERY_POINTER_PATTERNS = [
    r"(?:^|(?<=[।\n]))[^।\n]*ছবি[^।\n]*(?:নিচে|নীচে|উপরে)[^।\n]*।?",
    r"(?:^|(?<=[।\n]))[^।\n]*(?:নিচে|নীচে)[^।\n]*ছবি[^।\n]*(?:দেখ|দেওয়া|দিলাম)[^।\n]*।?",
    r"(?:^|(?<=[।\n]))\s*see the (?:photo|image)s? below[^.\n]*\.?",
]


_MISSING_PHOTO_PATTERNS = [
    r"(?:^|(?<=[।\n]))[^।\n]*ছবি[^।\n]*(?:সম্ভব হচ্ছে না|দেখানো যাচ্ছে না|দেওয়া যাচ্ছে না|দেয়া যাচ্ছে না)[^।\n]*।?",
    r"(?:^|(?<=[।\n]))[^।\n]*কোনো\s+ছবি[^।\n]*।?",
    r"(?:^|(?<=[।\n]))[^।\n]*(?:ছবি নেই|ছবি নাই)[^।\n]*।?",
    r"(?:^|(?<=[।\n]))[^।\n]*(?:পুরো|পুরা|full(?:\s+body)?|whole)[^।\n]*(?:ছবি নেই|ছবি নাই|photo (?:is )?not)[^।\n]*।?",
    r"(?:^|(?<=[।\n]))[^\n.]*(?:cannot|can't|can not)\s+show[^\n.]*(?:photo|image)[^\n.]*\.?",
    r"(?:^|(?<=[।\n]))[^\n.]*(?:no (?:photo|image)[^\n.]*(?:available|right now))[^\n.]*\.?",
]


def strip_false_missing_photos(text: str) -> str:
    """Drop 'we have no photo' lines when a gallery image is actually attached."""
    if not text:
        return text
    cleaned = text
    for pattern in _MISSING_PHOTO_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def strip_gallery_pointers(text: str) -> str:
    """Drop "photo shown below" lines when no gallery will be attached."""
    if not text:
        return text
    cleaned = text
    for pattern in _GALLERY_POINTER_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def filter_assistant_reply(text: str) -> str:
    """Strip markdown/noise only — do NOT truncate (truncation caused cut-off replies)."""
    if not text:
        return text

    # Model output mixes nukta encodings too, so normalise before anything matches on it.
    cleaned = nfc(text).strip()

    # Never show Google Drive folder links to farmers in chat — gallery is in-app.
    cleaned = re.sub(
        r"https?://(?:drive|docs)\.google\.com/\S+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"(?i)(গুগল\s*ড্রাইভ|google\s*drive)[^\n।.]*[।.]?",
        "",
        cleaned,
    )

    kept: list[str] = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            kept.append("")
            continue
        if any(re.match(p, stripped, re.IGNORECASE) for p in _NOISE_PATTERNS):
            continue
        kept.append(stripped)

    cleaned = "\n".join(kept).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = strip_forbidden_names(cleaned)
    return strip_leaked_metadata(cleaned)
