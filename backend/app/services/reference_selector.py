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
    is_asking_about_shown_image,
    last_shown_gallery,
)
from app.utils.drawing_queries import (
    query_is_how_it_works,
    query_wants_assembly_diagram,
    query_wants_technical_drawing,
)
from app.utils.image_labels import display_label
from app.utils.parts_suppliers import is_belt_price_query, is_belt_supplier_query

logger = logging.getLogger(__name__)

_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "belt": ("belt", "v-belt", "vbelt", "b65", "b-belt", "বেল্ট", "ভি-বেল্ট"),
    "motor": (
        "motor", "electric", "220v", "1.5 hp", "1.1 kw", "hp", "rpm", "capacitor",
        "burn", "generator", "kva", "nosto", "noshto", "broken",
        "মোটর", "বিদ্যুৎ", "জ্বল", "ধোঁয়া", "জেনারেটর",
    ),
    "sieve": (
        "sieve", "screen", "mesh", "net", "perforated", "shake", "shaking",
        "vibrat", "oscillat", "clog", "jam", "ঝরন", "চালুনি", "চালনি", "সিভ", "জাল", "ঝাঁক", "আটক",
    ),
    "blower": (
        "blower", "fan", "blade", "air blast", "wind", "intake", "weak air", "দুর্বল",
        "ব্লোয়ার", "পাখা", "বাতাস", "হাওয়া", "ধুল", "batash", "batash",
    ),
    "bearing": (
        "bearing", "6203", "6302", "ucp206", "p-206", "pillow", "block", "grinding",
        "noise", "grease", "কম্পন", "বিয়ারিং", "শব্দ",
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
        "blow away", "spill", "good rice", "clean grain", "grain loss",
        "ভালো ধান", "ধান উড়", "ধান উড়", "তুষের সাথে ধান",
    ),
    "pulley": ("pulley", "tension", "ratio", "পুলি", "অনুপাত"),
    "linkage": ("linkage", "connecting rod", "arm", "crank", "রড", "লিঙ্ক"),
    "discharge": ("discharge", "outlet", "chute", "নল", "আউটলেট", "নিষ্কাশন"),
    "blueprint": ("blueprint", "dimension", "drawing", "manufactur", "spec", "bom", "মাপ", "নকশা", "ড্রয়িং"),
    "shaft": ("shaft", "শ্যাফট", "শ্যাফ্ট"),
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
    "06": frozenset({"blower"}),
    "08": frozenset({"sieve"}),
    "09": frozenset({"sieve", "linkage"}),
    "10": frozenset({"belt", "pulley"}),
    "11": frozenset({"motor"}),
    "12": frozenset({"motor", "pulley"}),
    "13": frozenset({"blower", "pulley"}),
    "14": frozenset({"bearing"}),
    "15": frozenset({"bearing"}),
    "16": frozenset({"bearing", "sieve"}),
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
    "sieve": ("sieve", "ঝরন", "screen", "চালুনি", "চালনি", "সিভ"),
    "motor": ("motor", "মোটর", "generator"),
    "bearing": ("bearing", "বিয়ারিং", "pillow"),
    "blower": ("blower", "ব্লোয়ার", "fan"),
    "hopper": ("hopper", "হপার", "feed gate"),
    "shaft": ("shaft", "শ্যাফট", "small shaft", "sieve small"),
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


def _entry_haystack(entry: dict) -> str:
    return (
        f"{entry.get('image_name', '')} {entry.get('description', '')} "
        f"{entry.get('part_name', '')} {entry.get('title', '')} "
        f"{entry.get('part_paper', '')} "
        f"{' '.join(entry.get('keywords') or [])} "
        f"{' '.join(entry.get('related_symptoms_bn') or [])}"
    ).lower()


def _entry_topics(entry: dict) -> set[str]:
    haystack = _entry_haystack(entry)
    found = {
        topic
        for topic, hints in _SUBSYSTEM_HINTS.items()
        if any(h in haystack for h in hints)
    }
    slot = str(entry.get("photo_no") or "")
    found |= set(_PHOTO_SLOT_TOPICS.get(slot, ()))
    return found


def _is_overview_shot(entry: dict) -> bool:
    blob = f"{entry.get('image_name', '')} {entry.get('title', '')} {entry.get('part_paper', '')}".lower()
    return any(
        m in blob
        for m in ("full machine", "full_exterior", "full front", "full side", "পুরো মেশিন")
    )


def entry_is_on_topic(entry: dict, topics: set[str], query: str) -> bool:
    """False when the catalogue row is clearly about a different subsystem."""
    if not topics:
        return not _is_overview_shot(entry)
    if _is_overview_shot(entry) and not any(
        w in query.lower() for w in ("full", "পুরো", "whole", "সমগ্র", "বাইর")
    ):
        return False
    et = _entry_topics(entry)
    if not et:
        # Unknown row: keep only if the query asked for a drawing of that file type.
        source = entry.get("source")
        if source == "cad_drawing":
            return query_wants_technical_drawing(query)
        if source == "subassembly_drawing":
            return query_wants_assembly_diagram(query)
        return False
    return bool(et & topics)


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

    haystack = _entry_haystack(entry)
    query_lower = query.lower()
    score = 0.0
    source = entry.get("source")

    if not entry_is_on_topic(entry, topics, query):
        return 0.0
    if not topics and not (
        query_wants_technical_drawing(query)
        or query_wants_assembly_diagram(query)
        or asks_for_photos(query)
    ):
        return 0.0

    for token in _tokenize(query_lower):
        if len(token) < 3:
            continue
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

    for topic, keywords in _TOPIC_KEYWORDS.items():
        if topic not in topics:
            continue
        if any(_keyword_in_text(kw, query_lower) for kw in keywords) and any(
            _keyword_in_text(kw, haystack) for kw in keywords
        ):
            score += 4.0

    if source == "cad_drawing" and query_wants_technical_drawing(query):
        score += 8.0
    if source == "subassembly_drawing" and query_wants_assembly_diagram(query):
        score += 22.0
        title = f"{entry.get('title', '')} {entry.get('image_name', '')}".lower()
        if "main body" in title or "bom" in title:
            score += 14.0
    if query_wants_assembly_diagram(query):
        if source == "field_collection":
            score -= 22.0
        if source == "cad_drawing":
            if any(s in haystack for s in ("left side", "right side", "বাম পাশ", "ডান পাশ")):
                score -= 16.0
    if query_wants_technical_drawing(query) and not query_wants_assembly_diagram(query):
        if source == "cad_drawing":
            score += 6.0
        if source == "field_collection":
            score -= 8.0
    if "hopper" in topics and query_wants_technical_drawing(query):
        if source == "cad_drawing" and "hopper" in haystack:
            score += 16.0
    if "shaft" in topics and query_wants_technical_drawing(query):
        if source == "cad_drawing" and "shaft" in haystack:
            score += 18.0
        if source == "field_collection":
            score -= 10.0
    if query_is_how_it_works(query) and source == "field_collection":
        if "hopper" in haystack:
            score += 16.0
        if "belt" in haystack or "b65" in haystack:
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


def resolve_reference_image_paths(names: list[str] | None) -> list[Path]:
    """Resolve catalogue file names to existing paths."""
    paths: list[Path] = []
    seen: set[str] = set()
    for name in names or []:
        if not name or name in seen:
            continue
        path = _resolve_path(name)
        if path is None:
            continue
        paths.append(path)
        seen.add(name)
    return paths


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


def best_fault_for_query(query: str) -> dict | None:
    """High-confidence field-fault match for grounding Gemini (not the eager fallback)."""
    kb = get_knowledge_base()
    best: dict | None = None
    best_score = 0.0
    for ft in kb.fault_trees or []:
        score = _score_fault_match(ft, query)
        if score > best_score:
            best_score = score
            best = ft
    return best if best and best_score >= _MIN_FAULT_MATCH_SCORE else None


def build_grounding_context(
    user_text: str,
    history: list[dict[str, str]] | None = None,
    selected_paths: list[Path] | None = None,
) -> str:
    """Short on-topic brief for this turn — keeps the model off other subsystems."""
    if is_asking_about_shown_image(user_text or "", history):
        gallery = last_shown_gallery(history)
        labels = [str(g.get("label") or "").strip() for g in gallery if g.get("label")]
        return "\n".join(
            [
                "=== THIS TURN (farmer asks what the LAST shown photo is) ===",
                "Previous gallery labels (official name of those photos): "
                + ("; ".join(labels) or "(none shown)"),
                "Name the object in the photo. Do not rename it to a neighbouring part.",
                "=== END THIS TURN ===",
            ]
        )

    focus = build_conversation_focus(user_text or "", history)
    topics = sorted(_detect_query_topics(focus))
    lines = ["=== THIS TURN (stay on this topic only) ==="]
    if topics:
        lines.append("Farmer topic: " + ", ".join(topics))
    fault = best_fault_for_query(focus)
    if fault:
        symptom = fault.get("symptom_local_bn") or fault.get("symptom_paper") or ""
        part = fault.get("part_local_bn") or fault.get("part_paper") or ""
        lines.append(f"Topic lock (not a script to paste): {part} — {symptom}")
        lines.append(
            "Answer the current question. Use a field-note step only if this "
            "question needs it. Do not dump the whole field recipe."
        )
    kb = get_knowledge_base()
    shown: list[str] = []
    for path in selected_paths or []:
        entry = kb._by_name.get(path.name, {})
        label = (
            entry.get("part_paper")
            or entry.get("part_name")
            or entry.get("title")
            or path.name
        )
        shown.append(str(label).split("—")[-1].strip()[:60])
    if shown:
        lines.append("Gallery will show ONLY: " + "; ".join(shown))
        lines.append("You may say ছবি নিচে দেখানো হয়েছে. Do not mention other photos.")
    else:
        lines.append("No gallery this turn — do not say photos are shown below.")
    lines.append("Stay on the named part. Do not switch subsystems.")
    lines.append("=== END THIS TURN ===")
    return "\n".join(lines)


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
    wants_visuals = conversation_wants_visuals(user_text or "", history)
    # Symptom answers: at most 2 on-topic photos. Photo-asks can use the full limit.
    if not wants_visuals and not has_user_image:
        limit = min(limit, 2)

    min_score = settings.REFERENCE_IMAGE_MIN_SCORE
    if has_user_image:
        min_score = max(3.0, min_score - 1.0)
    if wants_visuals:
        min_score = max(3.5, min_score - 1.0)

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
    topics = _detect_query_topics(focus)

    chosen: list[Path] = []
    chosen_names: set[str] = set()
    chosen_labels: set[str] = set()

    def _add(entry: dict, score: float | None = None) -> bool:
        if len(chosen) >= limit:
            return False
        if score is not None and score < min_score:
            return False
        if not entry_is_on_topic(entry, topics, focus):
            return False
        name = entry.get("image_name")
        if not name or name in chosen_names:
            return False
        label = display_label(entry, name)
        if label in chosen_labels:
            return False
        path = _resolve_path(name)
        if path is None:
            return False
        chosen.append(path)
        chosen_names.add(name)
        chosen_labels.add(label)
        return True

    # Prefer LLM / caller-selected numbers when provided — still on-topic only.
    if preferred_numbers:
        score_by_num = {
            e.get("image_number"): s for s, e in scored_candidates
        }
        for num in preferred_numbers:
            entry = by_number.get(num)
            if entry:
                _add(entry, score_by_num.get(num, min_score))

    for score, entry in scored_candidates:
        if len(chosen) >= limit:
            break
        _add(entry, score)

    logger.info(
        "Selected %d images for focus=%r topics=%s: %s",
        len(chosen),
        focus[:80],
        sorted(topics),
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
