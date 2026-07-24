"""Light cleanup of assistant replies — remove noise, never cut mid-sentence."""

import re

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


def filter_assistant_reply(text: str) -> str:
    """Strip markdown/noise only — do NOT truncate (truncation caused cut-off replies)."""
    if not text:
        return text

    cleaned = text.strip()

    # Flatten markdown bold/italic markers the model sometimes adds.
    cleaned = re.sub(r"\*+([^*]+)\*+", r"\1", cleaned)

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
    return cleaned
