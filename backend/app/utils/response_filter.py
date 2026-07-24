"""Post-process assistant replies: keep them brief and on-point."""

import re

# ~7 short Bengali lines; hard cap prevents rambling in the UI.
MAX_REPLY_CHARS = 750

# Lines/sections often added by the model that add no value for the farmer.
_NOISE_PATTERNS = [
    r"^#{1,6}\s+.+$",  # markdown headings
    r"^\*\*.+\*\*$",  # bold-only lines
    r"^---+$",
    r"^উপসংহার.*",
    r"^সারসংক্ষেপ.*",
    r"^আমি\s+(একজন\s+)?AI.*",
    r"^As an AI.*",
    r"^I am an AI.*",
    r"^Note:.*",
    r"^Disclaimer:.*",
]


def filter_assistant_reply(text: str) -> str:
    """Trim filler and enforce a concise reply suitable for chat."""
    if not text:
        return text

    cleaned = text.strip()

    # Drop obvious noise lines.
    kept: list[str] = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(re.match(p, stripped, re.IGNORECASE) for p in _NOISE_PATTERNS):
            continue
        kept.append(stripped)
    cleaned = "\n".join(kept).strip()

    # Collapse excessive blank lines.
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # Hard character cap — cut at last sentence boundary when possible.
    if len(cleaned) > MAX_REPLY_CHARS:
        chunk = cleaned[:MAX_REPLY_CHARS]
        for sep in ("।\n", "?\n", "?\n", "। ", "? ", "! "):
            idx = chunk.rfind(sep)
            if idx > MAX_REPLY_CHARS // 2:
                cleaned = chunk[: idx + len(sep.rstrip())].strip()
                break
        else:
            cleaned = chunk.rstrip() + "…"

    return cleaned
