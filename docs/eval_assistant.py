#!/usr/bin/env python3
"""Independent evaluation of the BRRI Win2024 assistant (novel questions)."""

from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.gemini_service import gemini_service  # noqa: E402
from app.services.knowledge_base import reload_knowledge_base  # noqa: E402
from app.services.reference_selector import select_reference_images  # noqa: E402
from app.utils.canonical_replies import match_field_fault  # noqa: E402

# Questions deliberately NOT copied from fault_trees.json or form examples.
#
# "expect" keywords must be words a correct BANGLA answer would really use. English
# terms only earn a hit for part codes the assistant keeps in English (B65, UCP206) or
# for units the matcher folds from Bangla (হর্স পাওয়ার → hp, ১.৫ → 1.5). Prefer Bangla
# stems over full words so inflections match: "নিরাপ" covers both নিরাপদ and নিরাপত্তা.
NOVEL_TESTS = [
    {
        "id": "wet_grain",
        "question": "বর্ষায় ধান একটু ভেজা থাকলে Win2024 দিয়ে পরিষ্কার করলে ভালো ধান উড়ে যায়, কী করব?",
        "expect": ["air control", "বাতাস", "wet", "ভেজা", "feed", "gate"],
        "expect_images_any": ["field_03", "cad_11", "air_control"],
    },
    {
        "id": "first_use",
        "question": "নতুন মেশিন কিনেছি, প্রথমবার চালু করার আগে কী কী চেক করব?",
        "expect": ["বেল্ট", "মোটর", "বোল্ট", "বিয়ারিং", "গ্রিজ", "চেক"],
        "expect_images_any": [],
    },
    {
        "id": "straw_jam",
        "question": "গমের খড় হপারে আটকে যায়, দানা নামে না — কোন অংশ দেখব?",
        "expect": ["hopper", "gate", "feed", "হপার", "গেট"],
        "expect_images_any": ["hopper", "cad_16", "cad_17", "field_04"],
    },
    {
        "id": "generator_power",
        "question": "বাড়িতে জেনারেটর আছে 2kVA — এই Winnower চালানো যাবে?",
        "expect": ["kva", "কেভিএ", "hp", "kw", "মোটর", "1.5"],
        "expect_images_any": [],
    },
    {
        # The form lists three sieve types by size class only; exact hole diameters
        # are NOT in the collected data, so the assistant must not quote mm figures.
        "id": "mustard_sieve",
        "question": "সরিষা পরিষ্কার করতে কোন ঝরনি লাগবে?",
        "expect": ["sieve", "ঝরন", "ছোট", "small", "net", "তিন"],
        "expect_images_any": ["sieve", "cad_22", "field_08"],
        "forbid": ["6mm", "6 mm", "10mm", "10 mm", "13mm", "13 mm"],
    },
    {
        "id": "rust_frame",
        "question": "বৃষ্টির পর মেশিনের নরম প্লেটে মরিচা ধরেছে, কাজে সমস্যা হবে?",
        "expect": ["মরিচা", "পরিষ্কার", "শুকন", "রং", "ঘষ", "প্লেট"],
        "expect_images_any": [],
    },
    {
        "id": "cad_hopper_welder",
        "question": "হপার পার্ট-২ এর কাটিং ড্রয়িং দেখান, কামাই করতে হবে",
        "expect": ["হপার", "মাপ", "প্লেট", "ড্রয়িং", "কাট", "mm"],
        "expect_images_any": ["cad_17", "hopper"],
    },
    {
        "id": "blower_weak_not_fault",
        "question": "ব্লোয়ার ঘুরছে কিন্তু হাওয়া খুব দুর্বল, ধুল আলাদা হয় না",
        "expect": ["blower", "fan", "belt", "air", "ব্লোয়ার", "বেল্ট", "pulley"],
        "expect_images_any": ["field_05", "blower", "cad"],
    },
    {
        "id": "safety_belt",
        "question": "বাচ্চারা খেলতে গিয়ে বেল্টে হাত দিলে কী হতে পারে, কীভাবে সুরক্ষা?",
        "expect": ["বেল্ট", "কভার", "নিরাপ", "দুর্ঘটনা", "বন্ধ", "দূরে"],
        "expect_images_any": [],
    },
    {
        "id": "transport_loose",
        "question": "পিকআপে করে নিয়ে এসেছি, চালু করলে পুরো মেশিন কাঁপছে",
        "expect": ["bolt", "mount", "bearing", "level", "বোল্ট", "বিয়ারিং", "vibrat"],
        "expect_images_any": ["bearing", "field_14", "subasm"],
    },
    {
        "id": "wrong_belt_size",
        "question": "দোকানদার B-52 বেল্ট দিল, চলবে?",
        "expect": ["b65", "65", "belt", "no", "না", "বেল্ট", "inch"],
        "expect_images_any": ["field_10", "belt", "b65"],
    },
    {
        # Mentioning a shop is not a shopping question — this must stay a
        # "where is it mounted" answer, with no dealer list.
        "id": "belt_location_not_shopping",
        "question": "বেল্ট কোথায় লাগানো থাকে?",
        "expect": ["পুলি", "মোটর", "বেল্ট", "ব্লোয়ার"],
        "expect_images_any": ["field_10", "field_11", "belt", "pulley", "01_brri"],
        "forbid": ["০১৭১৮২৩২৪০৬", "ডিলার পয়েন্ট"],
    },
    {
        "id": "visual_followup",
        "question": "ছবি দিয়ে বুঝিয়ে দেন",
        "history": [{"role": "user", "content": "ঝরনি কাঁপছে না / নড়ছে না"}],
        "expect": ["6203", "bearing", "shaft", "ঝরন", "বিয়ারিং", "শ্যাফট"],
        "expect_images_any": ["field_09", "sieve", "cad_26", "6203"],
    },
    # --- Regression cases: data integrity against the collection form ---------
    {
        # The form has exactly ONE filled dealer row. Any other shop is invented.
        "id": "dealer_only_verified",
        "question": "নতুন B65 বেল্ট কিনতে হবে, কোথায় পাওয়া যাবে?",
        "expect": ["এসি আই মোটরস", "০১৭১৮২৩২৪০৬", "পটুয়াখালী", "b65"],
        "expect_images_any": [],
        "forbid": ["নিউ এগ্রো", "টিপু সুলতান", "০১৭১৮২৩১৪৯৬", "01718231496"],
    },
    {
        "id": "belt_price_no_gallery",
        "question": "বেল্টের দাম কত?",
        "expect": ["দাম", "ডিলার", "০১৭১৮২৩২৪০৬"],
        "expect_images_any": [],
        "expect_no_gallery": True,
        "forbid": ["নিউ এগ্রো", "টিপু সুলতান"],
    },
    {
        # Form says 1.5 HP / 1.1 kW / 1400 rpm. Older catalogue text said 0.5 HP.
        "id": "motor_rating",
        "question": "মোটরের ক্ষমতা কত এইচপি?",
        "expect": ["1.5", "১.৫", "hp", "kw", "1400"],
        "expect_images_any": [],
        "forbid": ["0.5 hp", "0.5hp", "০.৫"],
    },
    {
        # Form lists 6203 (sieve), UCP206 (pillow), 6302 (blower). Not 6306 / P-206.
        "id": "bearing_numbers",
        "question": "ঝরনি আর ব্লোয়ারে কোন কোন বিয়ারিং লাগে?",
        "expect": ["6203", "ucp206", "6302", "বিয়ারিং"],
        "expect_images_any": ["field_14", "field_15", "bearing"],
        "forbid": ["6306", "p-206"],
    },
    {
        "id": "no_drive_links",
        "question": "এয়ার কন্ট্রোল প্লেটের ছবি দেখান",
        "expect": ["এয়ার", "প্লেট", "বাতাস"],
        "expect_images_any": ["field_03", "cad_11", "air_control", "13_air_control"],
        "forbid": ["drive.google.com", "গুগল ড্রাইভ", "ড্রাইভ লিংক"],
    },
    {
        "id": "belt_tension_no_dealer_dump",
        "question": "বেল্ট একটু ঢিলা মনে হচ্ছে, কী করব?",
        "expect": ["টাইট", "বেল্ট", "পুলি", "tension"],
        "expect_images_any": ["field_10", "belt", "01_brri", "27_v_belt"],
        # The dealer block is allowed here only because a worn belt may genuinely need
        # replacing; what must not happen is the shopping list replacing the tension
        # advice, which the "expect" keywords above check for.
    },
    {
        "id": "no_leaked_meta",
        "question": "চিটা এত উড়ে যায় কেন?",
        "expect": ["বাতাস", "এয়ার", "কমা"],
        "expect_images_any": ["field_03", "air_control", "13_air_control", "field_05"],
        "forbid": ["show_images", "---meta", "suggestions", "{\"", "true (since"],
    },
    {
        "id": "weight_spec",
        "question": "মেশিনের ওজন কত?",
        "expect": ["৯৭", "97", "কেজি", "kg", "ওজন"],
        "expect_images_any": [],
    },
    {
        "id": "off_topic_refusal",
        "question": "আজকের আবহাওয়া কেমন থাকবে?",
        "expect": ["উইনোয়ার", "মেশিন", "সাহায্য", "প্রশ্ন"],
        "expect_images_any": [],
        "expect_no_gallery": True,
        "forbid": ["বৃষ্টি হবে", "তাপমাত্রা"],
    },
    {
        "id": "frame_material",
        "question": "মূল ফ্রেমের অ্যাঙ্গেল বারের মাপ কত?",
        "expect": ["38", "৩৮", "angle", "অ্যাঙ্গেল", "mm"],
        "expect_images_any": [],
    },
]


@dataclass
class Score:
    relevance: float
    grounded: float
    actionable: float
    language: float
    images: float
    notes: str

    @property
    def total(self) -> float:
        return self.relevance + self.grounded + self.actionable + self.language + self.images

    @property
    def pct(self) -> float:
        return round(100 * self.total / 25, 1)


def _has_bangla(text: str) -> bool:
    return bool(re.search(r"[\u0980-\u09FF]", text))


_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

# The assistant answers in Bangla, so "1.5 HP" comes back as "১.৫ হর্স পাওয়ার" and
# "UCP206" as "ইউসিপি২০৬". Fold those to Latin before keyword matching, otherwise a
# perfectly correct reply scores as a miss.
_BN_TERM_ALIASES = (
    ("হর্স পাওয়ার", " hp "),
    ("হর্সপাওয়ার", " hp "),
    ("এইচপি", " hp "),
    ("কিলোওয়াট", " kw "),
    ("আরপিএম", " rpm "),
    ("মিলিমিটার", " mm "),
    ("মিমি", " mm "),
    ("কেজি", " kg "),
    ("ইউসিপি", "ucp"),
    ("অ্যাঙ্গেল", " angle "),
    ("এঙ্গেল", " angle "),
)


def _normalize_for_match(text: str) -> str:
    # NFC first: য়/ও য়া arrive either precomposed (U+09DF) or as য + nukta, and the
    # two forms never compare equal as raw strings.
    lower = unicodedata.normalize("NFC", text or "").lower().translate(_BN_DIGITS)
    for bn, latin in _BN_TERM_ALIASES:
        lower = lower.replace(bn, latin)
    return re.sub(r"\s+", " ", lower)


def _keyword_hits(text: str, keywords: list[str]) -> int:
    normalized = _normalize_for_match(text)
    return sum(1 for k in keywords if _normalize_for_match(k).strip() in normalized)


def _score_images(names: list[str], expect_any: list[str]) -> tuple[float, str]:
    if not expect_any:
        return 3.0, "no image expectation"
    joined = " ".join(names).lower()
    hits = [e for e in expect_any if e.lower() in joined]
    if hits:
        return 5.0, f"matched: {hits[:3]}"
    if names:
        return 2.5, f"images but not ideal: {names[:3]}"
    return 0.5, "no images attached"


def _forbidden_hits(text: str, forbid: list[str]) -> list[str]:
    # Normalized both ways so "০.৫ এইচপি" is caught by the "0.5 hp" rule.
    normalized = _normalize_for_match(text)
    return [f for f in forbid if _normalize_for_match(f).strip() in normalized]


def _score_reply(
    question: str,
    reply: str,
    image_names: list[str],
    expect: list[str],
    expect_img: list[str],
    forbid: list[str] | None = None,
    show_gallery: bool | None = None,
    expect_no_gallery: bool = False,
) -> Score:
    if not reply or len(reply.strip()) < 20:
        return Score(0, 0, 0, 0, 0, "empty or too short")

    hits = _keyword_hits(reply, expect)
    rel = min(5.0, 2.0 + hits * 0.8) if hits else 1.5

    hallucination_red_flags = ["chatgpt", "openai", "as an ai", "আমি একটি এআই"]
    grounded = 4.0 if not any(r in reply.lower() for r in hallucination_red_flags) else 2.0
    if hits >= 2:
        grounded = min(5.0, grounded + 1.0)

    # Forbidden strings are data-integrity failures (invented dealers, wrong part
    # numbers, leaked prompt text). They zero out groundedness rather than nudge it.
    banned = _forbidden_hits(reply, forbid or [])
    if banned:
        grounded = 0.0

    actionable = 3.0
    if re.search(r"[১২৩456789]|^\s*[1-9]\.", reply, re.MULTILINE):
        actionable = 4.5
    if "সমাধান" in reply or "check" in reply.lower() or "পরীক্ষা" in reply:
        actionable = min(5.0, actionable + 0.5)

    language = 4.0 if _has_bangla(reply) else 2.0
    if len(reply) > 80 and _has_bangla(reply):
        language = min(5.0, language + 0.5)

    if expect_no_gallery:
        img_score = 5.0 if not show_gallery else 1.0
        img_note = "gallery correctly hidden" if not show_gallery else "GALLERY SHOWN but should be hidden"
    else:
        img_score, img_note = _score_images(image_names, expect_img)

    notes = f"kw={hits}/expect; img: {img_note}"
    if banned:
        notes += f"; FORBIDDEN: {banned}"
    return Score(rel, grounded, actionable, language, img_score, notes)


def run_eval() -> dict:
    reload_knowledge_base()
    if not gemini_service.is_configured:
        print("ERROR: GEMINI_API_KEY not set")
        sys.exit(1)

    results = []
    for i, test in enumerate(NOVEL_TESTS):
        q = test["question"]
        history = test.get("history", [])
        print(f"\n[{i+1}/{len(NOVEL_TESTS)}] {test['id']}: {q[:60]}…")

        refs = select_reference_images(q, history=history)
        img_names = [p.name for p in refs]
        fault = match_field_fault(q)

        try:
            result = gemini_service.chat_reply(history, q, refs)
            reply = result.text
            show = result.show_reference_images
        except Exception as exc:
            reply = f"API ERROR: {exc}"
            show = False

        score = _score_reply(
            q,
            reply,
            img_names,
            test["expect"],
            test["expect_images_any"],
            forbid=test.get("forbid"),
            show_gallery=show,
            expect_no_gallery=test.get("expect_no_gallery", False),
        )
        row = {
            "id": test["id"],
            "question": q,
            "reply": reply,
            "reply_len": len(reply),
            "images": img_names,
            "show_gallery": show,
            "forbidden_hits": _forbidden_hits(reply, test.get("forbid") or []),
            "field_fault_match": fault.get("field_key") if fault else None,
            "score_pct": score.pct,
            "score_detail": {
                "relevance": score.relevance,
                "grounded": score.grounded,
                "actionable": score.actionable,
                "language": score.language,
                "images": score.images,
            },
            "notes": score.notes,
        }
        results.append(row)
        print(f"  score={score.pct}% imgs={img_names[:2]} show={show}")
        time.sleep(1.2)

    avg_pct = round(sum(r["score_pct"] for r in results) / len(results), 1)
    violations = [r["id"] for r in results if r["forbidden_hits"]]

    def _passes(row: dict, threshold: float) -> bool:
        # A forbidden string means wrong data reached the farmer — never a pass.
        return row["score_pct"] >= threshold and not row["forbidden_hits"]

    summary = {
        "tests": len(results),
        "average_score_pct": avg_pct,
        "pass_rate_60pct": round(100 * sum(1 for r in results if _passes(r, 60)) / len(results), 1),
        "pass_rate_70pct": round(100 * sum(1 for r in results if _passes(r, 70)) / len(results), 1),
        "with_images": sum(1 for r in results if r["images"]),
        "forbidden_violations": violations,
        "results": results,
    }
    return summary


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "eval_results.json"
    summary = run_eval()
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== SUMMARY ===")
    print(f"Average score: {summary['average_score_pct']}%")
    print(f"Pass rate (≥60%): {summary['pass_rate_60pct']}%")
    print(f"Pass rate (≥70%): {summary['pass_rate_70pct']}%")
    print(f"Tests with images: {summary['with_images']}/{summary['tests']}")
    if summary["forbidden_violations"]:
        print(f"DATA INTEGRITY FAILURES: {summary['forbidden_violations']}")
    else:
        print("Data integrity: no forbidden strings in any reply")
    print(f"Full report → {out}")
