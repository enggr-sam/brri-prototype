"""Instant local replies for greetings and unambiguous machine facts.

These skip Gemini. Do NOT put field-fault matching here — that matcher is too
eager on novel questions and would trade diagnosis accuracy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.config import settings
from app.services.knowledge_base import get_knowledge_base
from app.utils.bangla_text import nfc
from app.utils.follow_ups import local_suggestions
from app.utils.parts_suppliers import (
    format_belt_price_reply_bn,
    format_belt_suppliers_bn,
    is_belt_price_query,
    is_belt_supplier_query,
)

_GREETING_EXACT = {
    "hi",
    "hii",
    "hiii",
    "hello",
    "helloo",
    "hey",
    "helo",
    "hola",
    "yo",
    "salam",
    "salaam",
    "assalamu alaikum",
    "assalamualaikum",
    "as salamu alaykum",
    "as-salamu alaykum",
    "good morning",
    "good evening",
    "good afternoon",
    "good night",
    "how are you",
    "how r u",
    "whats up",
    "what's up",
    "হ্যালো",
    "হেলো",
    "হাই",
    "হায়",
    "সালাম",
    "সালাম আলাইকুম",
    "আসসালামু আলাইকুম",
    "আসসালামুআলাইকুম",
    "ওয়ালাইকুম সালাম",
    "কেমন আছো",
    "কেমন আছেন",
    "কেমন আছ",
    "কেমন আছো আপনি",
    "নমস্কার",
    "আদাব",
}

_GREETING_PREFIX = (
    "hello",
    "hi ",
    "hey ",
    "হ্যালো",
    "হাই",
    "সালাম",
)

# If these appear, the message is about the machine (or a real question) — not a hello.
_MACHINE_OR_QUESTION_HINTS = (
    "winnower",
    "win2024",
    "brri",
    "মেশিন",
    "যন্ত্র",
    "বেল্ট",
    "belt",
    "মোটর",
    "motor",
    "ঝরন",
    "sieve",
    "ব্লোয়ার",
    "ব্লোয়ার",
    "blower",
    "হপার",
    "hopper",
    "ধান",
    "চিটা",
    "বিয়ারিং",
    "bearing",
    "পুলি",
    "pulley",
    "ছবি",
    "photo",
    "দাম",
    "সমস্যা",
    "নষ্ট",
    "মেরামত",
)

_PROBLEM_HINTS = (
    "সমস্যা",
    "নষ্ট",
    "গরম",
    "শব্দ",
    "কাঁপ",
    "চলছে না",
    "চালু হচ্ছে না",
    "দুর্বল",
    "গন্ধ",
    "পোড়া",
    "পোড়া",
    "হচ্ছে না",
    "আটকে",
    "ভাঙ",
    "ভাং",
)

_MOTOR_RATING_TERMS = (
    "hp",
    "এইচপি",
    "হর্স",
    "ক্ষমতা",
    "কিলোওয়াট",
    "কিলোওয়াট",
    "kw",
    "rpm",
    "আরপিএম",
    "স্পেসিফিকেশন",
    "specification",
    "পাওয়ার",
    "পাওয়ার",
    "power",
)

_QUESTION_MARKERS = ("কত", "কতো", "কী", "কি ", "what", "কতখানি", "কতটা")

_GREETING_REPLY_BN = (
    "আসসালামু আলাইকুম। আমি শুধু বিআরআরআই উইনোয়ার ২০২৪ (BRRI Win2024) "
    "মেশিন নিয়ে সাহায্য করি — যন্ত্রাংশ, স্পেক, খুঁত আর মেরামত।\n\n"
    "মেশিনে কী সমস্যা হচ্ছে লিখুন, অথবা ছবি পাঠান।"
)

_GREETING_SUGGESTIONS = (
    "মেশিনে কী সমস্যা হচ্ছে?",
    "মোটরের ক্ষমতা কত এইচপি?",
    "B65 বেল্ট কোথায় পাওয়া যাবে?",
)


@dataclass
class FastPathHit:
    text: str
    show_reference_images: bool = False
    suggestions: list[str] = field(default_factory=list)


def _folded(text: str) -> str:
    t = nfc(text or "").strip()
    t = re.sub(r"[!?.~,।]+$", "", t).strip()
    t = re.sub(r"\s+", " ", t)
    return t.lower()


def is_greeting(text: str) -> bool:
    """True only when the whole message is a hello — not 'hello, my belt is loose'."""
    folded = _folded(text)
    if not folded or len(folded) > 48:
        return False
    if any(hint in folded for hint in _MACHINE_OR_QUESTION_HINTS):
        return False
    if folded in _GREETING_EXACT:
        return True
    # "hello there" / "hi ভাই" — still a greeting if it starts like one and is short.
    if len(folded) <= 24 and any(folded.startswith(p) for p in _GREETING_PREFIX):
        return True
    return False


def is_motor_rating_query(text: str) -> bool:
    """Ask for the motor HP/kW rating — not a motor fault."""
    lower = nfc(text or "").lower()
    if not any(term in lower for term in ("মোটর", "motor")):
        return False
    if any(term in lower for term in _PROBLEM_HINTS):
        return False
    has_rating = any(term in lower for term in _MOTOR_RATING_TERMS)
    has_question = any(term in lower for term in _QUESTION_MARKERS)
    return has_rating and has_question


def is_weight_query(text: str) -> bool:
    """Ask for machine mass — not vibration / 'feels heavy' faults."""
    lower = nfc(text or "").lower()
    if any(term in lower for term in ("কাঁপ", "ভাইব্রেট", "vibrat", "সমস্যা", "নষ্ট")):
        return False
    has_weight = any(term in lower for term in ("ওজন", "weight", "কেজি", "kg"))
    has_question = any(term in lower for term in _QUESTION_MARKERS)
    return has_weight and has_question


def _bn_num(value: object) -> str:
    return str(value).translate(str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯"))


def format_motor_rating_bn() -> str:
    motor = get_knowledge_base().machine_data.get("motor") or {}
    hp = motor.get("power_hp", 1.5)
    kw = motor.get("power_kw", 1.1)
    rpm = motor.get("speed_rpm", 1400)
    return (
        f"বিআরআরআই উইনোয়ার ২০২৪ (BRRI Win2024) মেশিনে "
        f"{_bn_num(hp)} হর্সপাওয়ার ({hp} HP / {kw} কিলোওয়াট) মোটর ব্যবহার করা হয়, "
        f"গতি {_bn_num(rpm)} আরপিএম ({rpm} rpm)।"
    )


def format_weight_bn() -> str:
    dims = get_knowledge_base().machine_data.get("dimensions") or {}
    kg = dims.get("weight_kg", 97.86)
    return (
        f"বিআরআরআই উইনোয়ার ২০২৪ মেশিনের ওজন {_bn_num(kg)} কেজি ({kg} kg)।"
        )


def try_fast_path(
    user_text: str,
    history: list[dict[str, str]] | None = None,
    *,
    has_user_image: bool = False,
) -> FastPathHit | None:
    """Return a local reply when the question is unambiguous; else None (use Gemini)."""
    if not settings.ENABLE_LOCAL_FAST_PATH:
        return None
    # A photo of a part always needs vision — even if the caption is "hello".
    if has_user_image:
        return None

    text = nfc(user_text or "").strip()
    if not text:
        return None

    if is_greeting(text):
        return FastPathHit(
            text=_GREETING_REPLY_BN,
            suggestions=list(_GREETING_SUGGESTIONS),
        )

    if is_belt_price_query(text, history):
        return FastPathHit(
            text=format_belt_price_reply_bn(),
            suggestions=local_suggestions(text, history),
        )

    if is_belt_supplier_query(text):
        return FastPathHit(
            text=format_belt_suppliers_bn(),
            suggestions=local_suggestions(text, history),
        )

    if is_motor_rating_query(text):
        return FastPathHit(
            text=format_motor_rating_bn(),
            suggestions=local_suggestions(text, history),
        )

    if is_weight_query(text):
        return FastPathHit(
            text=format_weight_bn(),
            suggestions=local_suggestions(text, history),
        )

    return None
