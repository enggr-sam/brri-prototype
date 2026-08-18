"""Intelligent reference-image retrieval for BRRI Winnower chat.

Thought process (not one-off hard maps):
1. Build a conversation *focus* from substantive history + current turn.
2. Rank the full catalogue (field photos, CAD, PDF refs) against that focus.
3. Prefer fault-tree / field matches when symptoms align.
4. Return a shortlist; an optional LLM reasoner may narrow it further.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path

from app.config import settings
from app.services.knowledge_base import FIELD_PHOTO_BASE, get_knowledge_base
from app.utils.conversation_focus import (
    asks_for_photos,
    build_conversation_focus,
    conversation_wants_visuals,
)
from app.utils.drawing_queries import query_wants_assembly_diagram, query_wants_technical_drawing
from app.utils.parts_suppliers import is_belt_price_query, is_belt_supplier_query

logger = logging.getLogger(__name__)

_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "belt": ("belt", "v-belt", "vbelt", "b65", "b-belt", "বেল্ট", "ভি-বেল্ট"),
    "motor": (
        "motor", "electric", "220v", "1.5 hp", "1.1 kw", "hp", "rpm", "capacitor",
        "burn", "generator", "kva", "মোটর", "বিদ্যুৎ", "জ্বল", "ধোঁয়া", "জেনারেটর",
    ),
    "sieve": (
        "sieve", "screen", "mesh", "net", "perforated", "shake", "shaking",
        "vibrat", "oscillat", "clog", "jam", "ঝরন", "চালুনি", "জাল", "ঝাঁক", "আটক",
    ),
    "blower": (
        "blower", "fan", "blade", "air blast", "wind", "intake", "weak air", "দুর্বল",
        "ব্লোয়ার", "পাখা", "বাতাস", "হাওয়া", "ধুল", "batash", "batash",
    ),
    "bearing": (
        "bearing", "6203", "6302", "ucp206", "p-206", "pillow", "block", "grinding",
        "noise", "vibrat", "grease", "কাঁপ", "কম্পন", "বিয়ারিং", "শব্দ",
    ),
    "hopper": (
        "hopper", "feed", "gate", "flap", "grain flow", "হপার", "গেট", "ফিড", "ফ্লাপ",
    ),
    "air_control": (
        "air control", "airflow", "air flow", "wind speed", "chaff", "dust",
        "বাতাস", "নিয়ন্ত্রণ", "তুষ", "চিট", "চিটা", "chita", "ভেসে", "উড়", "উড়",
        "উড়ে", "batash", "control", "কন্ট্রোল", "এয়ার",
    ),
    "grain_loss": (
        "blow away", "spill", "good rice", "clean grain",
        "ধান", "চাল", "নষ্ট", "ঝর", "বের হয়",
    ),
    "pulley": ("pulley", "tension", "ratio", "পুলি", "অনুপাত"),
    "linkage": ("linkage", "connecting rod", "arm", "crank", "রড", "লিঙ্ক"),
    "discharge": ("discharge", "outlet", "chute", "নল", "আউটলেট", "নিষ্কাশন"),
    "blueprint": ("blueprint", "dimension", "drawing", "manufactur", "spec", "bom", "মাপ"),
}

_STOP_FAULT_KEYWORDS = frozenset({
    "na", "না", "yes", "the", "and", "for", "with",
    "যায়", "যায়", "হয়", "হয়", "হয়ে", "কম", "ধান", "সাথে", "বেশি",
})

_FAULT_TOPIC_HINTS: dict[str, tuple[str, ...]] = {
    "Fault belt": ("belt",),
    "Fault air": ("air_control", "grain_loss", "blower"),
    "Fault sieve motion": ("sieve", "linkage"),
    "Fault motor": ("motor",),
    "Fault bearing": ("bearing",),
    "Fault blower": ("blower", "air_control"),
    "Fault feed": ("hopper",),
    "Fault multicrop": ("sieve",),
}

_PHOTO_SLOT_TOPICS: dict[str, frozenset[str]] = {
    "03": frozenset({"air_control", "grain_loss", "blower"}),
    "04": frozenset({"hopper"}),
    "05": frozenset({"blower", "air_control"}),
    "08": frozenset({"sieve"}),
    "09": frozenset({"sieve", "linkage"}),
    "10": frozenset({"belt", "pulley"}),
    "11": frozenset({"motor", "pulley"}),
    "14": frozenset({"bearing"}),
    "15": frozenset({"bearing"}),
}

_MIN_FAULT_MATCH_SCORE = 8.0
_CANDIDATE_POOL = 8

# Photos of paperwork (spec sheet, BOM list). Useful when someone asks for specs or
# dimensions, misleading when they describe a symptom.
_PAPER_DOCUMENT_MARKERS = (
    "technical document",
    "technical specifications",
    "bill of materials",
    "specifications' sheet",
    "master 'technical",
    "parts list",
)

# Soft subsystem boosts inside descriptions (not rigid image-number maps).
_SUBSYSTEM_HINTS: dict[str, tuple[str, ...]] = {
    "air_control": (
        "air control", "air intake", "blower intake", "এয়ার", "বাতাস নিয়ন্ত্রণ",
        "control plate", "batash",
    ),
    "belt": ("belt", "b65", "v-belt", "বেল্ট"),
    "sieve": ("sieve", "ঝরন", "screen", "চালুনি"),
    "motor": ("motor", "মোটর", "generator"),
    "bearing": ("bearing", "বিয়ারিং", "pillow"),
    "blower": ("blower", "ব্লোয়ার", "fan"),
    "hopper": ("hopper", "হপার", "feed gate"),
}


def user_requests_visual_help(text: str) -> bool:
    return asks_for_photos(text)


def build_image_selection_query(
    user_text: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    """Backward-compatible alias → conversation focus."""
    return build_conversation_focus(user_text, history)


def _tokenize(text: str) -> set[str]:
    text = text.lower()
    return {t for t in re.split(r"[^\w\u0980-\u09FF]+", text) if len(t) >= 2}


@lru_cache(maxsize=512)
def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    """Match ``keyword`` only at the start of a word.

    Plain substring matching misreads Bangla: হাওয়া (wind) hides inside আবহাওয়া
    (weather), so a weather question used to score blower photos. Bangla attaches
    suffixes rather than prefixes (বাতাস → বাতাসের), so guarding the left edge alone
    keeps inflected forms matching while dropping accidental hits — the same guard
    stops "arm" from firing on "farmer".
    """
    return re.compile(rf"(?<![\w\u0980-\u09FF]){re.escape(keyword.lower())}")


def _keyword_in_text(keyword: str, text: str) -> bool:
    return bool(_keyword_pattern(keyword).search(text))


def _detect_query_topics(query: str) -> set[str]:
    ql = query.lower()
    return {
        topic
        for topic, keywords in _TOPIC_KEYWORDS.items()
        if any(_keyword_in_text(kw, ql) for kw in keywords)
    }


def _entry_by_number(entries: list[dict], number: int) -> dict | None:
    for entry in entries:
        if entry.get("image_number") == number:
            return entry
    return None


def _resolve_path(image_name: str) -> Path | None:
    if not image_name:
        return None
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


def _score_entry(entry: dict, query: str, topics: set[str]) -> float:
    if not query or not query.strip():
        return 0.0

    haystack = (
        f"{entry.get('image_name', '')} {entry.get('description', '')} "
        f"{entry.get('part_name', '')} {entry.get('title', '')} "
        f"{' '.join(entry.get('keywords') or [])} "
        f"{' '.join(entry.get('related_symptoms_bn') or [])}"
    ).lower()
    query_lower = query.lower()
    score = 0.0
    source = entry.get("source")

    for token in _tokenize(query_lower):
        if token in haystack:
            score += 2.0

    for kw in entry.get("keywords") or []:
        if kw.lower() in query_lower:
            score += 5.0

    for symptom in entry.get("related_symptoms_bn") or []:
        if symptom and symptom.lower() in query_lower:
            score += 8.0

    # Soft topic ↔ subsystem alignment (intelligent match, not hard ID maps).
    for topic in topics:
        hints = _SUBSYSTEM_HINTS.get(topic, ())
        if hints and any(h in haystack for h in hints):
            score += 7.0

    for keywords in _TOPIC_KEYWORDS.values():
        if any(kw in query_lower for kw in keywords) and any(kw in haystack for kw in keywords):
            score += 4.0

    if source == "cad_drawing" and query_wants_technical_drawing(query):
        score += 8.0
    if source == "subassembly_drawing" and query_wants_assembly_diagram(query):
        score += 8.0
    if source == "field_collection":
        score += 3.0  # Prefer real photos when scores are close
        slot = entry.get("photo_no") or ""
        allowed = _PHOTO_SLOT_TOPICS.get(slot)
        if allowed and topics and not (topics & allowed):
            score -= 12.0
        elif allowed and topics & allowed:
            score += 6.0

    # A photo of the spec sheet answers "what size / which bearing", not "why is my
    # grain blowing away".
    if any(marker in haystack for marker in _PAPER_DOCUMENT_MARKERS):
        wants_paper = bool(topics & {"blueprint"}) or query_wants_technical_drawing(query)
        score += 6.0 if wants_paper else -14.0

    # Penalize clearly off-topic subassemblies when focus is air/belt/etc.
    if source == "subassembly_drawing" and topics:
        label = f"{entry.get('part_name', '')} {entry.get('title', '')}".lower()
        if "air_control" in topics and not any(
            x in label or x in haystack for x in ("air", "বাতাস", "control", "blower")
        ):
            if any(x in label for x in ("sieve", "show cover", "hopper", "motor")):
                score -= 15.0

    return score


def _score_fault_match(fault: dict, query: str) -> float:
    ql = query.lower()
    tokens = _tokenize(query)
    score = 0.0

    symptom = (fault.get("symptom_local_bn") or "").lower()
    part_paper = (fault.get("part_paper") or "").lower()
    part_local = (fault.get("part_local_bn") or "").lower()
    field_key = fault.get("field_key") or ""

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

    if field_key == "Fault sieve motion":
        sieve_words = ("ঝরন", "ঝরনি", "চালুনি", "sieve", "screen", "শ্যাফট", "shaft")
        if "কাঁপ" in ql and not any(w in ql for w in sieve_words):
            score -= 10.0

    if field_key == "Fault motor":
        if not (query_topics & {"motor"} or "মোটর" in ql or "generator" in ql):
            if "কম" in ql or "slow" in ql:
                score -= 6.0

    if field_key == "Fault blower":
        if query_topics & {"blower", "air_control"} or "ব্লোয়ার" in ql:
            score += 4.0

    if field_key == "Fault air":
        if query_topics & {"air_control", "grain_loss", "blower"} or "বাতাস" in ql or "batash" in ql:
            score += 8.0

    if field_key == "Fault bearing":
        if ("কাঁপ" in ql or "vibrat" in ql) and not any(
            w in ql for w in ("ঝরন", "sieve", "screen")
        ):
            score += 9.0

    return score


def _fault_boosted_numbers(query: str) -> dict[int, float]:
    kb = get_knowledge_base()
    boosts: dict[int, float] = {}
    if not kb.fault_trees:
        return boosts

    seen_fault: set[str] = set()
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
            boosts[num] = max(boosts.get(num, 0.0), match_score)
    return boosts


def _dedupe_near_identical(scored: list[tuple[float, dict]]) -> list[tuple[float, dict]]:
    """Keep one entry per drawing title.

    The form repeats a sub-assembly title across every row of that assembly, and all
    those rows share one catalogue description — so they score identically and would
    otherwise fill the shortlist with copies of the same label.
    """
    out: list[tuple[float, dict]] = []
    seen_titles: set[str] = set()
    for score, entry in scored:
        title = (entry.get("title") or "").strip().lower()
        if title and entry.get("source") == "subassembly_drawing":
            if title in seen_titles:
                continue
            seen_titles.add(title)
        out.append((score, entry))
    return out


def retrieve_scored_candidates(
    user_text: str | None = None,
    history: list[dict[str, str]] | None = None,
    *,
    pool: int = _CANDIDATE_POOL,
) -> list[tuple[float, dict]]:
    """Rank catalogue entries for the conversation focus, best first."""
    kb = get_knowledge_base()
    entries = kb.reference_images
    if not entries:
        return []

    focus = build_conversation_focus(user_text or "", history)
    if is_belt_supplier_query(focus) or is_belt_price_query(user_text or "", history):
        return []

    topics = _detect_query_topics(focus)
    fault_boosts = _fault_boosted_numbers(focus)
    scored: list[tuple[float, dict]] = []

    for entry in entries:
        num = entry.get("image_number")
        score = _score_entry(entry, focus, topics)
        if num is not None and num in fault_boosts:
            score += fault_boosts[num]
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda item: (-item[0], item[1].get("image_number", 999)))
    scored = _dedupe_near_identical(scored)[:pool]
    logger.info(
        "Image candidates (%d) for focus=%r topics=%s: %s",
        len(scored),
        focus[:90],
        sorted(topics),
        [(e.get("image_number"), round(s, 1)) for s, e in scored],
    )
    return scored


def retrieve_image_candidates(
    user_text: str | None = None,
    history: list[dict[str, str]] | None = None,
    *,
    pool: int = _CANDIDATE_POOL,
) -> list[dict]:
    """Shortlist of catalogue entries for the conversation focus."""
    return [e for _, e in retrieve_scored_candidates(user_text, history, pool=pool)]


def select_reference_images(
    user_text: str | None = None,
    limit: int | None = None,
    *,
    has_user_image: bool = False,
    history: list[dict[str, str]] | None = None,
    preferred_numbers: list[int] | None = None,
) -> list[Path]:
    """Return up to ``limit`` paths using focus ranking (+ optional reasoner picks)."""
    limit = limit or settings.MAX_REFERENCE_IMAGES
    min_score = settings.REFERENCE_IMAGE_MIN_SCORE
    if has_user_image:
        min_score = max(2.0, min_score - 2.0)
    if conversation_wants_visuals(user_text or "", history):
        min_score = max(1.5, min_score - 2.0)

    kb = get_knowledge_base()
    scored_candidates = retrieve_scored_candidates(user_text, history)
    if not scored_candidates:
        return []

    by_number = {
        e["image_number"]: e
        for e in kb.reference_images
        if e.get("image_number") is not None
    }
    focus = build_conversation_focus(user_text or "", history)

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

    # Prefer LLM / caller-selected numbers when provided.
    if preferred_numbers:
        for num in preferred_numbers:
            entry = by_number.get(num)
            if entry:
                _add(entry)

    # Fill from ranked candidates above threshold.
    wants_visuals = conversation_wants_visuals(user_text or "", history)
    for score, entry in scored_candidates:
        if len(chosen) >= limit:
            break
        if not wants_visuals and score < min_score:
            continue
        # When farmer asked for photos, allow slightly weaker but on-topic hits.
        if wants_visuals and score < max(2.0, min_score - 1):
            continue
        _add(entry)

    logger.info(
        "Selected %d images for focus=%r: %s",
        len(chosen),
        focus[:80],
        [p.name for p in chosen],
    )
    return chosen


def order_reference_images_by_relevance(
    paths: list[Path],
    query: str,
) -> list[Path]:
    query = (query or "").strip()
    if not paths or not query:
        return paths
    kb = get_knowledge_base()
    topics = _detect_query_topics(query)
    scored: list[tuple[float, Path]] = []
    for path in paths:
        entry = kb._by_name.get(path.name, {})
        scored.append((_score_entry(entry, query, topics), path))
    scored.sort(key=lambda item: (-item[0], item[1].name))
    return [path for _, path in scored]
