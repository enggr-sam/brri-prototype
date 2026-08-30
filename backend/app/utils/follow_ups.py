"""Follow-up chips: AI after the reply, with a local fallback."""

from __future__ import annotations

import json
import re

from app.utils.canonical_replies import match_field_fault
from app.utils.conversation_focus import build_conversation_focus

SUGGESTION_LIMIT = 5

_BANNED = ("ঝরনি", "ঝরনী", "জাল", "চালনা", "বিআরআরআই উইনোয়ার", "উইনোয়ার ২০২৪")

_TOPIC_SUGGESTIONS: dict[str, tuple[str, ...]] = {
    "air_control": (
        "এয়ার কন্ট্রোল প্লেট কোথায়?",
        "বাতাস কতটুকু কমাব?",
        "চিটা আলাদা হচ্ছে না কেন?",
        "ভালো ধান উড়ে যাচ্ছে কেন?",
    ),
    "belt": (
        "বেল্ট কতটা টাইট হওয়া উচিত?",
        "বেল্ট বদলাব কীভাবে?",
        "B65 বেল্ট কোথায় পাওয়া যাবে?",
        "বেল্ট পিছলে যাচ্ছে কেন?",
    ),
    "sieve": (
        "চালনি কীভাবে পরিষ্কার করব?",
        "কোন ফসলে কোন চালনি লাগবে?",
        "চালনি নড়ছে না কেন?",
        "চালনির ছিদ্র বড় না ছোট?",
    ),
    "motor": (
        "মোটর গরম হচ্ছে কেন?",
        "মোটরের ক্ষমতা কত?",
        "মোটর চালু হচ্ছে না কেন?",
        "কত কেভিএ জেনারেটর লাগবে?",
    ),
    "bearing": (
        "বিয়ারিং কখন বদলাব?",
        "কোন সাইজের বিয়ারিং লাগবে?",
        "গ্রীজ কতদিন পর দিব?",
        "বিয়ারিং থেকে শব্দ হচ্ছে কেন?",
    ),
    "blower": (
        "ব্লোয়ারের হাওয়া দুর্বল কেন?",
        "ব্লোয়ার পরিষ্কার করব কীভাবে?",
        "ব্লোয়ার ইউনিটের নকশা দেখাবেন?",
        "ফ্যানের ব্যাস কত?",
    ),
    "hopper": (
        "ফিড গেট কতটা খুলব?",
        "হপারে দানা আটকে যায় কেন?",
        "হপার পরিষ্কার রাখব কীভাবে?",
        "হপারের নকশা দেখাবেন?",
    ),
    "pulley": (
        "পুলির মাপ কত?",
        "পুলি সোজা আছে কীভাবে বুঝব?",
        "বেল্ট পিছলে যাচ্ছে কেন?",
    ),
    "shaft": (
        "শ্যাফটের মাপ কত?",
        "শ্যাফটের নকশা দেখাবেন?",
        "শ্যাফট বাঁকা হলে কী হয়?",
    ),
}

_DEFAULT_SUGGESTIONS = (
    "Winnower কীভাবে কাজ করে?",
    "চালু করার আগে কী কী দেখব?",
    "নিয়মিত রক্ষণাবেক্ষণ কীভাবে করব?",
    "B65 বেল্ট কোথায় পাওয়া যাবে?",
    "কোন চালনি কোন ফসলে লাগে?",
    "ব্লোয়ারের হাওয়া দুর্বল কেন?",
    "হপারে ধান আটকে যায় কেন?",
)


def _clean_item(text: str) -> str:
    t = (text or "").strip().strip("\"'`“”")
    t = re.sub(r"^\d+[.)]\s*", "", t)
    if any(bad in t for bad in _BANNED):
        t = (
            t.replace("ঝরনী", "চালনি")
            .replace("ঝরনি", "চালনি")
            .replace("জাল", "চালনি")
            .replace("চালনা", "চালনি")
        )
    return t


def parse_suggestion_list(raw: str, *, limit: int = SUGGESTION_LIMIT) -> list[str]:
    text = (raw or "").strip()
    if not text:
        return []
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    blob = re.search(r"\[.*\]", text, re.DOTALL)
    if blob:
        text = blob.group(0)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None
    items: list[str] = []
    if isinstance(data, list):
        items = [str(x) for x in data]
    elif isinstance(data, dict):
        items = [str(x) for x in (data.get("suggestions") or data.get("questions") or [])]
    else:
        items = [ln for ln in raw.splitlines() if ln.strip()]
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        q = _clean_item(item)
        if len(q) < 8 or len(q) > 90:
            continue
        if q in seen:
            continue
        seen.add(q)
        out.append(q)
        if len(out) >= limit:
            break
    return out


def followup_prompt(user_text: str, reply_text: str) -> str:
    return (
        "You write the farmer's NEXT questions after a BRRI Win2024 support reply.\n"
        "Read the QUESTION and the ANSWER. Then invent 5 short follow-ups.\n\n"
        f"QUESTION:\n{(user_text or '').strip()}\n\n"
        f"ANSWER:\n{(reply_text or '').strip()[:900]}\n\n"
        "Rules:\n"
        "- Spoken Bangla. One line each. A farmer would tap these next.\n"
        "- Each question must follow THIS answer (same part, next step, or a missing detail).\n"
        "- No generic filler like 'আর কোন সমস্যা হতে পারে'.\n"
        "- Screen word: চালনি or সিভ. Never জাল, ঝরনি, চালনা.\n"
        "- Do not write the machine name in Bangla.\n"
        "- Do not invent kg/h, wages, or a part that is not in the answer.\n"
        '- JSON only: ["q1","q2","q3","q4","q5"]\n'
    )


def local_suggestions(
    user_text: str,
    history: list[dict[str, str]] | None = None,
    *,
    reply_text: str = "",
    limit: int = SUGGESTION_LIMIT,
) -> list[str]:
    """Topic chips if the model call is skipped or thin."""
    from app.services.reference_selector import _detect_query_topics

    focus = build_conversation_focus(user_text or "", history)
    if reply_text:
        focus = f"{focus} {reply_text[:400]}"
    topics = _detect_query_topics(focus)

    picks: list[str] = []
    fault = match_field_fault(user_text or "")
    if fault:
        part = (fault.get("part_local_bn") or fault.get("part_paper") or "").strip()
        if part:
            picks.append(f"{part} ঠিক আছে কীভাবে বুঝব?")

    for topic in sorted(topics):
        for suggestion in _TOPIC_SUGGESTIONS.get(topic, ()):
            if suggestion not in picks:
                picks.append(suggestion)
            if len(picks) >= limit:
                return picks[:limit]

    for suggestion in _DEFAULT_SUGGESTIONS:
        if len(picks) >= limit:
            break
        if suggestion not in picks:
            picks.append(suggestion)

    return picks[:limit]
