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
from app.services.knowledge_base import FIELD_PHOTO_BASE, get_knowledge_base
from app.utils.drawing_queries import query_wants_assembly_diagram, query_wants_technical_drawing

logger = logging.getLogger(__name__)

# Anchor catalogue numbers always included when ``limit`` allows (specs + overview).
_ANCHOR_NUMBERS = (5, 2)

# Topic → keywords (English + common Bangla terms farmers may use).
_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "belt": (
        "belt", "v-belt", "vbelt", "b65", "b-belt",
        "বেল্ট", "ভি-বেল্ট",
    ),
    "motor": (
        "motor", "electric", "220v", "1.5 hp", "1.1 kw", "hp", "rpm", "capacitor", "burn",
        "generator", "kva", "মোটর", "বিদ্যুৎ", "জ্বল", "ধোঁয়া", "জেনারেটর",
    ),
    "sieve": (
        "sieve", "screen", "mesh", "net", "perforated", "shake", "shaking",
        "vibrat", "oscillat", "clog", "jam",
        "ঝরন", "চালুনি", "জাল", "ঝাঁক", "আটক",
    ),
    "blower": (
        "blower", "fan", "blade", "air blast", "wind", "intake", "weak air", "দুর্বল",
        "ব্লোয়ার", "পাখা", "বাতাস", "হাওয়া", "ধুল",
    ),
    "bearing": (
        "bearing", "6203", "6302", "ucp206", "p-206", "p206", "p-207", "pillow", "block",
        "grinding", "noise", "vibrat", "grease", "shake", "কাঁপ", "কম্পন",
        "বিয়ারিং", "শব্দ",
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
        # Require belt wording — do not fire on bare "slip"/"crack" alone.
        (
            "belt", "বেল্ট", "b65", "v-belt", "v belt", "ভি-বেল্ট",
            "বেল্ট পিছল", "বেল্ট ছিঁড়", "belt slip", "belt crack",
        ),
        (1, 27, 20, 18),
    ),
    (
        ("sieve", "ঝরন", "চালুনি", "জাল", "ঝাঁক", "screen", "shake", "আটক"),
        (28, 16, 31, 30),
    ),
    (
        ("motor", "মোটর", "220v", "1.5 hp", "1.1 kw", "generator", "kva", "ধোঁয়া", "জ্বল"),
        (1, 20, 23, 5, 111),
    ),
    (
        ("bearing", "বিয়ারিং", "6203", "6302", "ucp206", "pillow", "grinding", "কম্পন", "কাঁপ"),
        (314, 315, 31, 30, 13, 6),
    ),
    (
        ("blower", "ব্লোয়ার", "weak air", "দুর্বল", "হাওয়া কম", "air blast", "fan blade"),
        (105, 6, 7),
    ),
    (
        ("hopper", "হপার", "feed gate", "grain control", "আটক", "খড়", "straw"),
        (104, 11, 12),
    ),
]

_IMAGE_REQUEST_MARKERS = (
    "ছবি", "photo", "picture", "image", "দেখান", "দেখিয়", "দেখাই",
    "বুঝিয়", "বুঝাই", "visual", "diagram",
)

# Weak tokens from auto-generated fault keywords — must not alone trigger a match.
_STOP_FAULT_KEYWORDS = frozenset({
    "na", "না", "yes", "the", "and", "for", "with",
    "যায়", "যায়", "হয়", "হয়", "হয়ে", "কম", "ধান", "সাথে", "বেশি",
    "পাত", "নিয়ন্ত্রণ", "সমানভাবে", "যাচ্ছে", "পড়ছে", "ঠিকমতো",
    "ব্যবহারে", "পরিষ্কার", "ভুল", "তিন", "প্রকার", "বল", "হয়",
})

# Which query topics must appear before attaching a field photo for that fault.
_FAULT_TOPIC_HINTS: dict[str, tuple[str, ...]] = {
    "Fault belt": ("belt",),
    "Fault air": ("air_control", "grain_loss", "blower"),
    "Fault sieve motion": ("sieve", "linkage"),
    "Fault motor": ("motor",),
    "Fault bearing": ("bearing",),
    "Fault blower": ("blower", "air_control"),
    "Fault feed": ("hopper", "grain_control"),
    "Fault multicrop": ("sieve",),
}

_MIN_FAULT_MATCH_SCORE = 8.0

# Field photo slot → acceptable query topics (blocks sieve/motor on hopper/blower queries).
_PHOTO_SLOT_TOPICS: dict[str, frozenset[str]] = {
    "03": frozenset({"air_control", "grain_loss", "blower"}),
    "04": frozenset({"hopper", "grain_control"}),
    "05": frozenset({"blower", "air_control"}),
    "08": frozenset({"sieve"}),
    "09": frozenset({"sieve", "linkage"}),
    "10": frozenset({"belt", "pulley"}),
    "11": frozenset({"motor", "pulley"}),
    "14": frozenset({"bearing"}),
    "15": frozenset({"bearing"}),
}


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

    haystack = (
        f"{entry.get('image_name', '')} {entry.get('description', '')} "
        f"{entry.get('part_name', '')} {entry.get('title', '')} "
        f"{' '.join(entry.get('keywords') or [])}"
    ).lower()
    query_lower = query.lower()
    score = 0.0
    source = entry.get("source")

    # Token overlap (description / filename contains query words).
    for token in _tokenize(query_lower):
        if token in haystack:
            score += 2.0

    # Explicit keyword list on CAD / sub-assembly entries.
    for kw in entry.get("keywords") or []:
        if kw.lower() in query_lower:
            score += 5.0

    # Boost technical drawings when user asks for dimensions / fabrication.
    if source == "cad_drawing" and query_wants_technical_drawing(query):
        score += 8.0
    if source == "subassembly_drawing" and query_wants_assembly_diagram(query):
        score += 8.0
    if source == "cad_drawing" and not query_wants_assembly_diagram(query):
        for token in _tokenize((entry.get("part_name") or "").lower()):
            if token in query_lower:
                score += 6.0

    # Topic-level boost when both query and entry relate to the same subsystem.
    for keywords in _TOPIC_KEYWORDS.values():
        query_hit = any(kw in query_lower for kw in keywords)
        entry_hit = any(kw in haystack for kw in keywords)
        if query_hit and entry_hit:
            score += 6.0

    return score


def _detect_query_topics(query: str) -> set[str]:
    ql = query.lower()
    found: set[str] = set()
    for topic, keywords in _TOPIC_KEYWORDS.items():
        if any(kw in ql for kw in keywords):
            found.add(topic)
    return found


def _score_fault_match(fault: dict, query: str) -> float:
    """Score how well a field-collected fault entry matches the user query."""
    ql = query.lower()
    tokens = _tokenize(query)
    score = 0.0

    symptom = (fault.get("symptom_local_bn") or "").lower()
    part_paper = (fault.get("part_paper") or "").lower()
    part_local = (fault.get("part_local_bn") or "").lower()
    field_key = fault.get("field_key") or ""

    # Strong: distinctive symptom phrase present in query.
    for phrase in (symptom, part_local):
        if len(phrase) >= 8 and phrase in ql:
            score += 12.0

    for kw in fault.get("keywords") or []:
        kw_l = kw.lower()
        if len(kw_l) < 3 or kw_l in _STOP_FAULT_KEYWORDS:
            continue
        if kw_l in ql:
            score += 5.0 if len(kw_l) >= 5 else 3.0

    for token in tokens:
        if len(token) < 3 or token in _STOP_FAULT_KEYWORDS:
            continue
        if token in part_paper or token in part_local:
            score += 4.0
        elif token in symptom:
            score += 2.0

    query_topics = _detect_query_topics(query)
    hints = _FAULT_TOPIC_HINTS.get(field_key, ())
    if hints and query_topics & set(hints):
        score += 7.0
    elif hints and query_topics and not (query_topics & set(hints)):
        score -= 6.0

    # Whole-machine vibration ≠ sieve not shaking.
    if field_key == "Fault sieve motion":
        sieve_words = ("ঝরন", "ঝরনি", "চালুনি", "sieve", "screen", "শ্যাফট", "shaft")
        if "কাঁপ" in ql and not any(w in ql for w in sieve_words):
            score -= 10.0

    # Motor fault needs motor/generator context, not generic "slow/weak".
    if field_key == "Fault motor":
        if not (query_topics & {"motor"} or "মোটর" in ql or "generator" in ql or "জেনারেটর" in ql):
            if "কম" in ql or "slow" in ql:
                score -= 6.0

    # Blower weak air should not attach motor/sieve photos.
    if field_key == "Fault blower":
        if query_topics & {"blower"} or "ব্লোয়ার" in ql or "দুর্বল" in ql:
            score += 4.0

    # Whole-machine shake/vibration → bearings, not sieve motion.
    if field_key == "Fault bearing":
        if ("কাঁপ" in ql or "vibrat" in ql or "shake" in ql) and not any(
            w in ql for w in ("ঝরন", "ঝরনি", "sieve", "screen", "চালুনi")
        ):
            score += 9.0

    return score


def _collected_issue_numbers(query: str) -> list[int]:
    """Map user text to field-collected photo catalogue numbers (#101–120)."""
    kb = get_knowledge_base()
    if not kb.fault_trees:
        return []

    seen_fault: set[str] = set()
    scored: list[tuple[float, int]] = []

    for ft in kb.fault_trees:
        fault_id = ft.get("id") or ft.get("field_key") or ""
        if fault_id in seen_fault:
            continue
        match_score = _score_fault_match(ft, query)
        if match_score < _MIN_FAULT_MATCH_SCORE:
            continue
        seen_fault.add(fault_id)
        for pno in ft.get("photo_numbers") or []:
            try:
                num = FIELD_PHOTO_BASE + int(pno)
            except (TypeError, ValueError):
                continue
            scored.append((match_score, num))

    scored.sort(key=lambda x: (-x[0], x[1]))
    seen_nums: set[int] = set()
    ordered: list[int] = []
    for _, num in scored:
        if num not in seen_nums:
            seen_nums.add(num)
            ordered.append(num)
    return ordered


def _technical_drawing_numbers(query: str, entries: list[dict]) -> list[int]:
    """Rank CAD / sub-assembly catalogue numbers for drawing-related queries."""
    ql = query.lower()
    tokens = _tokenize(query)
    wants_cad = query_wants_technical_drawing(query)
    wants_asm = query_wants_assembly_diagram(query)
    scored: list[tuple[float, int]] = []

    for entry in entries:
        source = entry.get("source")
        if source not in ("cad_drawing", "subassembly_drawing"):
            continue
        num = entry.get("image_number")
        if num is None:
            continue

        score = 0.0
        label = f"{entry.get('part_name', '')} {entry.get('title', '')}".lower()
        for kw in entry.get("keywords") or []:
            if kw.lower() in ql:
                score += 5.0
        for token in tokens:
            if token in label or token in (entry.get("description") or "").lower():
                score += 3.0

        if source == "cad_drawing":
            pn = (entry.get("part_name") or "").lower()
            if pn:
                pn_norm = pn.replace("-", " ").replace("  ", " ")
                ql_norm = ql.replace("-", " ").replace("  ", " ")
                if pn in ql or pn_norm in ql_norm:
                    score += 14.0
                if "hopper" in pn and ("hopper" in ql or "হপার" in ql):
                    score += 6.0
                    if ("part-2" in pn or "part 2" in pn) and (
                        "2" in ql or "২" in ql or "part" in ql or "পার্ট" in ql
                    ):
                        score += 12.0

        if source == "cad_drawing":
            if wants_cad:
                score += 6.0
            if wants_asm and not wants_cad:
                score *= 0.5
        if source == "subassembly_drawing":
            if wants_asm:
                score += 6.0

        if score >= 5.0:
            scored.append((score, num))

    scored.sort(key=lambda x: (-x[0], x[1]))
    seen: set[int] = set()
    ordered: list[int] = []
    for _, num in scored:
        if num not in seen:
            seen.add(num)
            ordered.append(num)
    return ordered


def _resolve_path(image_name: str) -> Path | None:
    for base in (
        settings.reference_images_dir,
        settings.collected_photos_dir,
        settings.collected_cad_dir,
        settings.collected_subassembly_dir,
    ):
        path = base / image_name
        if path.is_file():
            return path
    return None


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
    if is_belt_supplier_query(query) or is_belt_price_query(query, history):
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

    # Field-collected fault → photo slot matches (#101–120) — prefer over PDF refs.
    for num in _collected_issue_numbers(query):
        entry = _entry_by_number(entries, num)
        if entry:
            _add(entry)

    # CAD cutting drawings + sub-assembly diagrams (#201+, #301+).
    for num in _technical_drawing_numbers(query, entries):
        entry = _entry_by_number(entries, num)
        if entry:
            _add(entry)

    # Curated PDF reference images for known farmer symptoms (Bangla + English).
    for num in _issue_matched_numbers(query):
        entry = _entry_by_number(entries, num)
        if entry:
            _add(entry)

    if query:
        query_topics = _detect_query_topics(query)
        for score, entry in ranked:
            if score < min_score:
                break
            if entry.get("source") == "field_collection":
                slot = entry.get("photo_no") or ""
                allowed = _PHOTO_SLOT_TOPICS.get(slot)
                if allowed and query_topics and not (query_topics & allowed):
                    continue
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
