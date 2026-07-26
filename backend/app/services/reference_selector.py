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
        "হপার", "গেট", "দানা", "ঢাল", "ফিড", "ফ্লাপ", "সবুজ",
    ),
    "air_control": (
        "air control", "airflow", "air flow", "wind speed", "chaff", "dust",
        "বাতাস", "নিয়ন্ত্রণ", "তুষ", "ধুল", "চিট", "চিটা", "chita", "ভেসে", "উড়", "উড়",
        "উড়ে", "ময়লা", "আলাদা",
    ),
    "grain_loss": (
        "blow away", "spill", "good rice", "clean grain", "losing grain",
        "ধান", "চাল", "চাউল", "নষ্ট", "পড়", "ঝর", "বের হয়", "বের হচ্ছ",
    ),
    "pulley": (
        "pulley", "cast-iron", "groove", "tension",
        "ratio", "ration", "speed ratio", "diameter",
        "পুলি", "অনুপাত",
    ),
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

# Strong symptom → catalogue image numbers (shown when query matches any keyword).
_ISSUE_IMAGE_NUMBERS: list[tuple[tuple[str, ...], tuple[int, ...]]] = [
    (
        (
            "chita",
            "chita ure",
            "ure jai",
            "ure jay",
            "keno eto",
            "এত বেশi",
            "এত বেশি",
            "চিট", "চিটা", "chaff", "তুষ", "ধান বের", "চাল বের", "উড়", "উড়", "উড়ে",
            "ভেসে", "বাতাস বেশি", "air control", "wind speed", "good rice",
            "blow away",
        ),
        (13, 14, 10, 11, 32),
    ),
    (
        ("belt", "বেল্ট", "b65", "slip", "slipping", "পিছল", "ছিঁড়", "v-belt"),
        (1, 27, 20, 18),
    ),
    (
        ("sieve", "ঝরন", "চালুনি", "জাল", "ঝাঁক", "screen", "shake", "আটক"),
        (28, 16, 31, 30),
    ),
    (
        ("motor", "মোটর", "220v", "0.5 hp", "ধোঁয়া", "জ্বল"),
        (1, 20, 23, 5),
    ),
    (
        ("bearing", "বিয়ারিং", "6306", "p-206", "pillow", "grinding", "কম্পন"),
        (31, 30, 13, 6),
    ),
]

_IMAGE_REQUEST_MARKERS = (
    "ছবি", "photo", "picture", "image", "দেখান", "দেখিয়", "দেখাই",
    "বুঝিয়", "বুঝাই", "visual", "diagram",
)


from app.utils.parts_suppliers import is_belt_price_query, is_belt_supplier_query


def user_requests_visual_help(text: str) -> bool:
    """True when the farmer explicitly asks for pictures or visual explanation."""
    lower = (text or "").lower()
    return any(m in lower for m in _IMAGE_REQUEST_MARKERS)


def build_image_selection_query(
    user_text: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    """Combine current message with recent user context for image matching.

    Follow-ups like “ছবি দিয়ে বুঝিয়ে দেন” need the prior symptom text.
    """
    text = (user_text or "").strip()
    if not text:
        return ""

    if history and (user_requests_visual_help(text) or len(text) < 40):
        prior_user = [
            (m.get("content") or "").strip()
            for m in history
            if m.get("role") == "user"
        ]
        if prior_user:
            combined = f"{prior_user[-1]} {text}".strip()
            if combined != text:
                logger.debug("Image query expanded with prior user message.")
            return combined
    return text


def _issue_matched_numbers(query: str) -> list[int]:
    ql = query.lower()
    seen: set[int] = set()
    ordered: list[int] = []
    for keywords, numbers in _ISSUE_IMAGE_NUMBERS:
        if any(kw in ql for kw in keywords):
            for num in numbers:
                if num not in seen:
                    seen.add(num)
                    ordered.append(num)
    return ordered


def _entry_by_number(entries: list[dict], number: int) -> dict | None:
    for entry in entries:
        if entry.get("image_number") == number:
            return entry
    return None


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


def _rank_entries(entries: list[dict], query: str) -> list[tuple[float, dict]]:
    """Sort catalogue entries by relevance (highest score first)."""
    query = query.strip()
    scored: list[tuple[float, dict]] = []
    for entry in entries:
        if query:
            score = _score_entry(entry, query)
        else:
            num = entry.get("image_number") or 999
            score = 10.0 if num in _ANCHOR_NUMBERS else max(0.0, 5.0 - num * 0.01)
        scored.append((score, entry))
    scored.sort(key=lambda item: (-item[0], item[1].get("image_number", 999)))
    return scored


def order_reference_images_by_relevance(
    paths: list[Path],
    query: str,
) -> list[Path]:
    """Re-sort selected images so the most relevant appear first in the gallery."""
    query = (query or "").strip()
    if not paths or not query:
        return paths

    kb = get_knowledge_base()
    scored: list[tuple[float, Path]] = []
    for path in paths:
        entry = kb._by_name.get(path.name, {})
        scored.append((_score_entry(entry, query), path))
    scored.sort(key=lambda item: (-item[0], item[1].name))
    return [path for _, path in scored]


def select_reference_images(
    user_text: str | None = None,
    limit: int | None = None,
    *,
    has_user_image: bool = False,
    history: list[dict[str, str]] | None = None,
) -> list[Path]:
    """Return up to ``limit`` reference image paths, most relevant first.

    Only images scoring above ``REFERENCE_IMAGE_MIN_SCORE`` are included.
    Known symptom patterns (e.g. chaff with grain) always pick curated photos.
    """
    limit = limit or settings.MAX_REFERENCE_IMAGES
    min_score = settings.REFERENCE_IMAGE_MIN_SCORE
    if has_user_image:
        min_score = max(2.0, min_score - 2.0)

    kb = get_knowledge_base()
    entries = kb.reference_images
    if not entries:
        return []

    query = build_image_selection_query(user_text or "", history)
    if is_belt_supplier_query(query) or is_belt_price_query(query):
        logger.info("Skipping reference images for belt price/supplier query.")
        return []

    wants_photos = user_requests_visual_help(user_text or "")
    if wants_photos:
        min_score = max(2.0, min_score - 1.5)

    ranked = _rank_entries(entries, query)

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

    # Curated images for known farmer symptoms (Bangla + English).
    for num in _issue_matched_numbers(query):
        entry = _entry_by_number(entries, num)
        if entry:
            _add(entry)

    if query:
        for score, entry in ranked:
            if score < min_score:
                break
            _add(entry)
    elif has_user_image:
        for score, entry in ranked:
            if score < min_score:
                break
            _add(entry)

    logger.info(
        "Selected %d reference images (min_score=%.1f, visual_help=%s) for query=%r: %s",
        len(chosen),
        min_score,
        wants_photos,
        query[:80] if query else "(none)",
        [p.name for p in chosen],
    )
    return chosen
