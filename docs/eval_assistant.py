#!/usr/bin/env python3
"""Independent evaluation of the BRRI Win2024 assistant (novel questions)."""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.gemini_service import gemini_service  # noqa: E402
from app.services.knowledge_base import reload_knowledge_base  # noqa: E402
from app.services.reference_selector import select_reference_images  # noqa: E402
from app.utils.canonical_replies import match_field_fault  # noqa: E402

# Questions deliberately NOT copied from fault_trees.json or form examples.
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
        "expect": ["belt", "motor", "bolt", "বেল্ট", "মোটর", "check"],
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
        "expect": ["220", "motor", "hp", "kw", "মোটর", "বিদ্যুৎ"],
        "expect_images_any": [],
    },
    {
        "id": "mustard_sieve",
        "question": "সরিষা পরিষ্কার করতে 6mm নাকি 10mm ঝরনি লাগবে?",
        "expect": ["sieve", "6", "10", "13", "mm", "ঝরন", "net"],
        "expect_images_any": ["sieve", "cad_22", "field_08"],
    },
    {
        "id": "rust_frame",
        "question": "বৃষ্টির পর মেশিনের নরম প্লেটে মরিচা ধরেছে, কাজে সমস্যা হবে?",
        "expect": ["rust", "steel", "frame", "মরিচা", "plate"],
        "expect_images_any": [],
    },
    {
        "id": "cad_hopper_welder",
        "question": "হপার পার্ট-২ এর কাটিং ড্রয়িং দেখান, কামাই করতে হবে",
        "expect": ["hopper", "drawing", "dimension", "হপার", "plate"],
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
        "expect": ["belt", "guard", "stop", "বেল্ট", "নিরাপদ", "power"],
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
        "id": "visual_followup",
        "question": "ছবি দিয়ে বুঝিয়ে দেন",
        "history": [{"role": "user", "content": "ঝরনি কাঁপছে না / নড়ছে না"}],
        "expect": ["6203", "bearing", "shaft", "ঝরন", "বিয়ারিং", "শ্যাফট"],
        "expect_images_any": ["field_09", "sieve", "cad_26", "6203"],
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


def _keyword_hits(text: str, keywords: list[str]) -> int:
    lower = text.lower()
    return sum(1 for k in keywords if k.lower() in lower)


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


def _score_reply(question: str, reply: str, image_names: list[str], expect: list[str], expect_img: list[str]) -> Score:
    if not reply or len(reply.strip()) < 20:
        return Score(0, 0, 0, 0, 0, "empty or too short")

    hits = _keyword_hits(reply, expect)
    rel = min(5.0, 2.0 + hits * 0.8) if hits else 1.5

    hallucination_red_flags = ["chatgpt", "openai", "as an ai", "আমি একটি এআই"]
    grounded = 4.0 if not any(r in reply.lower() for r in hallucination_red_flags) else 2.0
    if hits >= 2:
        grounded = min(5.0, grounded + 1.0)

    actionable = 3.0
    if re.search(r"[১২৩456789]|^\s*[1-9]\.", reply, re.MULTILINE):
        actionable = 4.5
    if "সমাধান" in reply or "check" in reply.lower() or "পরীক্ষা" in reply:
        actionable = min(5.0, actionable + 0.5)

    language = 4.0 if _has_bangla(reply) else 2.0
    if len(reply) > 80 and _has_bangla(reply):
        language = min(5.0, language + 0.5)

    img_score, img_note = _score_images(image_names, expect_img)
    notes = f"kw={hits}/expect; img: {img_note}"
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

        score = _score_reply(q, reply, img_names, test["expect"], test["expect_images_any"])
        row = {
            "id": test["id"],
            "question": q,
            "reply": reply,
            "reply_len": len(reply),
            "images": img_names,
            "show_gallery": show,
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
    summary = {
        "tests": len(results),
        "average_score_pct": avg_pct,
        "pass_rate_60pct": round(100 * sum(1 for r in results if r["score_pct"] >= 60) / len(results), 1),
        "pass_rate_70pct": round(100 * sum(1 for r in results if r["score_pct"] >= 70) / len(results), 1),
        "with_images": sum(1 for r in results if r["images"]),
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
    print(f"Full report → {out}")
