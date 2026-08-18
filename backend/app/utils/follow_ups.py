"""Local Bangla follow-up suggestions.

The polish pass returns suggestions in its META block, but that pass is skipped
when the draft is already complete. These topic-based suggestions keep the
follow-up chips working without spending an extra model call.
"""

from __future__ import annotations

from app.utils.canonical_replies import match_field_fault
from app.utils.conversation_focus import build_conversation_focus

_TOPIC_SUGGESTIONS: dict[str, tuple[str, ...]] = {
    "air_control": (
        "এয়ার কন্ট্রোল প্লেট কোথায় আছে?",
        "বাতাস কতটুকু কমাব?",
        "চিটা আলাদা হচ্ছে না কেন?",
    ),
    "belt": (
        "বেল্ট কতটা টাইট হওয়া উচিত?",
        "বেল্ট বদলানোর নিয়ম কী?",
        "B65 বেল্ট কোথায় পাওয়া যাবে?",
    ),
    "sieve": (
        "ঝরনি কীভাবে পরিষ্কার করব?",
        "কোন ফসলে কোন ঝরনি লাগবে?",
        "ঝরনি নড়ছে না কেন?",
    ),
    "motor": (
        "মোটর গরম হচ্ছে কেন?",
        "মোটরের স্পেসিফিকেশন কী?",
        "মোটর চালু হচ্ছে না কেন?",
    ),
    "bearing": (
        "বিয়ারিং কখন বদলাতে হবে?",
        "কোন সাইজের বিয়ারিং লাগবে?",
        "গ্রীজ কতদিন পর দিতে হবে?",
    ),
    "blower": (
        "ব্লোয়ারের হাওয়া দুর্বল কেন?",
        "ব্লোয়ার পরিষ্কার করব কীভাবে?",
        "ব্লোয়ার কভার খুলব কীভাবে?",
    ),
    "hopper": (
        "ফিড গেট কতটা খুলব?",
        "হপারে দানা আটকে যায় কেন?",
        "হপার পরিষ্কার রাখার নিয়ম?",
    ),
    "pulley": (
        "পুলির মাপ কত?",
        "পুলি ঠিকভাবে বসেছে কীভাবে বুঝব?",
        "বেল্ট পিছলে যাচ্ছে কেন?",
    ),
}

_DEFAULT_SUGGESTIONS = (
    "মেশিনের নিয়মিত রক্ষণাবেক্ষণ কীভাবে করব?",
    "পরিষ্কার করার আগে কী কী দেখব?",
    "আর কোন অংশে সমস্যা হতে পারে?",
)


def local_suggestions(
    user_text: str,
    history: list[dict[str, str]] | None = None,
    *,
    limit: int = 3,
) -> list[str]:
    """Up to ``limit`` Bangla follow-ups for the current conversation topic."""
    from app.services.reference_selector import _detect_query_topics

    focus = build_conversation_focus(user_text or "", history)
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
