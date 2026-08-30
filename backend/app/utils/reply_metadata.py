"""Parse hidden metadata block (suggestions, image flag) from model replies."""

from __future__ import annotations

import json
import re

META_MARKER = "---META---"

# Leaked model metadata / malformed META fragments shown to users.
_LEAKED_LINE_MARKERS = (
    "show_images",
    '"suggestions"',
    "'suggestions'",
    "as mandated for belt",
    "mandated for belt buyer",
    "suggestions (2-3",
    "smart diagnostic follow-up",
    "follow-ups in bangla",
    "air control lever & feed gate",
    "since air control lever",
    "feed gate photo help",
)


def strip_leaked_metadata(text: str) -> str:
    """Remove ---META--- tails and JSON/meta lines the model sometimes leaks."""
    if not text:
        return text

    cleaned = text.strip()

    if META_MARKER in cleaned:
        cleaned = cleaned.split(META_MARKER, 1)[0].strip()
    elif "---META" in cleaned:
        cleaned = re.split(r"---META-+", cleaned, maxsplit=1)[0].strip()

    # Trailing JSON blob without marker.
    cleaned = re.sub(
        r'\s*\{[\s\n]*"suggestions"[\s\S]*?"show_images"[\s\S]*?\}\s*$',
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    kept: list[str] = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            kept.append("")
            continue
        lower = stripped.lower()
        if any(marker in lower for marker in _LEAKED_LINE_MARKERS):
            continue
        if re.match(r"^:\s*true\b", stripped, re.IGNORECASE):
            continue
        if stripped.startswith("*") and ("`" in stripped or "show_images" in lower):
            continue
        if re.search(r'["\'\`\[\]\{\}]', stripped) and (
            "show_images" in lower
            or "suggestions" in lower
            or "পাওয়া যায়" in stripped
            or "পরিবর্তন করব" in stripped
        ):
            continue
        kept.append(stripped)

    cleaned = "\n".join(kept).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def split_reply_metadata(text: str) -> tuple[str, dict]:
    """Split visible reply from trailing metadata block."""
    raw = text or ""

    if META_MARKER not in raw and "---META" not in raw:
        return strip_leaked_metadata(raw).strip(), {}

    if META_MARKER in raw:
        main, tail = raw.split(META_MARKER, 1)
    else:
        main, tail = re.split(r"---META-+", raw, maxsplit=1)

    main = strip_leaked_metadata(main)
    meta: dict = {"suggestions": [], "show_images": True}

    tail = tail.strip()
    if not tail:
        return main.strip(), meta

    json_match = re.search(r"\{.*\}", tail, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
            if isinstance(parsed.get("suggestions"), list):
                meta["suggestions"] = [
                    str(s).strip() for s in parsed["suggestions"] if str(s).strip()
                ][:5]
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
            meta["suggestions"] = [p.strip() for p in parts if p.strip()][:5]
        elif line.upper().startswith("IMAGES:"):
            val = line.split(":", 1)[1].strip().lower()
            meta["show_images"] = val in ("yes", "true", "1")

    return main.strip(), meta


def dumps_suggestions(items: list[str]) -> str | None:
    cleaned = [s.strip() for s in items if s and s.strip()]
    if not cleaned:
        return None
    return json.dumps(cleaned[:5], ensure_ascii=False)


def loads_suggestions(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return [str(s) for s in data][:5] if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []
