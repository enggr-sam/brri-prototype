"""Pick the most relevant reference images for a troubleshooting request.

Scores catalogue entries from ``reference_images.json`` against the user's
text (optional description or voice transcription). Always includes a few
"anchor" images (specs table + full machine overview) so the model retains
global context, then fills remaining slots with the highest-scoring matches.
"""

import logging
import re
from pathlib import Path

from app.config import settings
from app.services.knowledge_base import get_knowledge_base

logger = logging.getLogger(__name__)

# Anchor catalogue numbers always included when ``limit`` allows (specs + overview).
_ANCHOR_NUMBERS = (5, 2)

# Topic → keywords (English + common Bangla terms farmers may use).
_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "belt": (
        "belt", "v-belt", "vbelt", "b65", "b-belt", "slip", "slipping", "crack",
        "বেল্ট", "পিছল", "ছিঁড়", "রাবার",
    ),
    "motor": (
        "motor", "electric", "220v", "0.5 hp", "hp", "rpm", "capacitor", "burn",
        "মোটর", "বিদ্যুৎ", "জ্বল", "ধোঁয়া",
    ),
    "sieve": (
        "sieve", "screen", "mesh", "net", "perforated", "shake", "shaking",
        "vibrat", "oscillat", "clog", "jam",
        "ঝরন", "চালুনি", "জাল", "ঝাঁক", "আটক",
    ),
    "blower": (
        "blower", "fan", "blade", "air blast", "wind", "intake",
        "ব্লোয়ার", "পাখা", "বাতাস", "হাওয়া",
    ),
    "bearing": (
        "bearing", "6306", "p-206", "p206", "p-207", "pillow", "block", "grinding",
        "noise", "vibrat", "grease",
        "বিয়ারিং", "শব্দ", "কম্পন",
    ),
    "hopper": (
        "hopper", "feed", "gate", "flap", "grain flow", "pour",
        "হপার", "গেট", "দানা", "ঢাল",
    ),
    "air_control": (
        "air control", "airflow", "air flow", "wind speed", "chaff", "dust",
        "বাতাস", "নিয়ন্ত্রণ", "তুষ", "ধুল",
    ),
    "pulley": ("pulley", "pulley", "cast-iron", "groove", "tension", "পুলি"),
    "linkage": (
        "linkage", "connecting rod", "arm", "crank", "eccentric", "cam",
        "রড", "লিঙ্ক",
    ),
    "discharge": (
        "discharge", "outlet", "chute", "spill", "grain exit", "clean grain",
        "নল", "আউটলেট", "পড়", "নিষ্কাশন",
    ),
    "blueprint": (
        "blueprint", "dimension", "drawing", "manufactur", "spec", "bom",
        "খসড়া", "মাপ",
    ),
}


def _tokenize(text: str) -> set[str]:
    """Lowercase tokens from mixed English/Bangla text."""
    text = text.lower()
    return {t for t in re.split(r"[^\w\u0980-\u09FF]+", text) if len(t) >= 2}


def _score_entry(entry: dict, query: str) -> float:
    """Higher score = more relevant to the user's query."""
    if not query or not query.strip():
        return 0.0

    haystack = f"{entry.get('image_name', '')} {entry.get('description', '')}".lower()
    query_lower = query.lower()
    score = 0.0

    # Token overlap (description / filename contains query words).
    for token in _tokenize(query_lower):
        if token in haystack:
            score += 2.0

    # Topic-level boost when both query and entry relate to the same subsystem.
    for keywords in _TOPIC_KEYWORDS.values():
        query_hit = any(kw in query_lower for kw in keywords)
        entry_hit = any(kw in haystack for kw in keywords)
        if query_hit and entry_hit:
            score += 6.0

    return score


def _resolve_path(image_name: str) -> Path | None:
    path = settings.reference_images_dir / image_name
    return path if path.is_file() else None


def select_reference_images(
    user_text: str | None = None,
    limit: int | None = None,
) -> list[Path]:
    """Return up to ``limit`` reference image paths, chosen for relevance.

    * Anchors (specs + full overview) are included first.
    * Remaining slots go to highest-scoring catalogue entries for ``user_text``.
    * If there is no user text, fills with anchors plus low-numbered defaults.
    """
    limit = limit or settings.MAX_REFERENCE_IMAGES
    kb = get_knowledge_base()
    entries = kb.reference_images
    if not entries:
        return []

    chosen: list[Path] = []
    chosen_names: set[str] = set()

    def _add(entry: dict) -> bool:
        if len(chosen) >= limit:
            return False
        name = entry.get("image_name")
        if not name or name in chosen_names:
            return False
        path = _resolve_path(name)
        if path is None:
            return False
        chosen.append(path)
        chosen_names.add(name)
        return True

    # 1) Always pin anchor images (technical specs + full machine view).
    by_number = {e.get("image_number"): e for e in entries}
    for num in _ANCHOR_NUMBERS:
        entry = by_number.get(num)
        if entry:
            _add(entry)

    query = (user_text or "").strip()

    if query:
        # 2) Rank remaining entries by relevance to the user's words.
        ranked = sorted(
            entries,
            key=lambda e: _score_entry(e, query),
            reverse=True,
        )
        for entry in ranked:
            if _score_entry(entry, query) <= 0:
                break
            _add(entry)
    else:
        # 3) No query text: add early catalogue numbers for broad coverage.
        for entry in sorted(entries, key=lambda e: e.get("image_number", 999)):
            _add(entry)

    # 4) Back-fill if anchors + matches did not reach the limit.
    if len(chosen) < limit:
        for entry in sorted(entries, key=lambda e: e.get("image_number", 999)):
            _add(entry)
            if len(chosen) >= limit:
                break

    logger.info(
        "Selected %d reference images for query=%r: %s",
        len(chosen),
        query[:80] if query else "(none)",
        [p.name for p in chosen],
    )
    return chosen
