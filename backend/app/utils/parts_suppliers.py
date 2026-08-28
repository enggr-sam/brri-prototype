"""Inject B65 belt dealer info only when the farmer clearly needs it."""

from __future__ import annotations

import re

from app.services.knowledge_base import get_knowledge_base

_BELT_TERMS = ("belt", "বেল্ট", "b65", "v-belt", "v belt", "ভি-বেল্ট", "ভি বেল্ট")

_PRICE_TERMS = (
    "price",
    "dam",
    "দাম",
    "মূল্য",
    "cost",
    "rate",
    "কত টাকা",
    "কতটাকা",
    "টাকা কত",
)

# Wanting to obtain a belt.
_ACQUIRE_TERMS = (
    "পাব",
    "পাও",
    "pawa",
    "paowa",
    "kinbo",
    "কিনব",
    "কিনতে",
    "কেনা",
    "কেনার",
    "buy",
    "purchase",
    "order",
    "অর্ডার",
)

# Asking for a seller by name.
_DEALER_NOUNS = (
    "ডিলার",
    "dealer",
    "supplier",
    "বিক্রেতা",
)

# Where/shop words. These hint at shopping but do not establish it on their own:
# "বেল্ট কোথায় লাগানো থাকে?" asks for a location, and "দোকানদার B-52 বেল্ট দিল,
# চলবে?" asks whether a wrong-size belt will work.
_SHOP_CONTEXT_TERMS = (
    "কোথায়",
    "কোথায়",
    "kothai",
    "kothay",
    "where",
    "পাব",
    "পাও",
    "pawa",
    "paowa",
    "kinbo",
    "কিনব",
    "কিনতে",
    "buy",
    "ডিলার",
    "dealer",
    "দোকান",
    "supplier",
)

# Only when a NEW belt is clearly needed — not every slip/tension check.
_BUY_OR_REPLACE_TERMS = (
    "নতুন বেল্ট",
    "বেল্ট বদল",
    "বেল্ট কিন",
    "বেল্ট লাগবে",
    "replace the belt",
    "new belt",
    "buy a belt",
    "buy belt",
    "need a new belt",
    "কিনতে হবে",
    "বদলাতে হবে",
    "বদল লাগবে",
)


def _has_belt(text: str) -> bool:
    lower = (text or "").lower()
    return any(term in lower for term in _BELT_TERMS)


def _recent_user_mentions_belt(history: list[dict[str, str]] | None) -> bool:
    if not history:
        return False
    for msg in reversed(history[-4:]):
        if msg.get("role") == "user" and _has_belt(msg.get("content") or ""):
            return True
    return False


def is_belt_price_query(
    text: str,
    history: list[dict[str, str]] | None = None,
) -> bool:
    """Farmer asks the price of the B65 belt — not a generic 'price/kemon'."""
    lower = (text or "").lower().strip()
    if not lower:
        return False
    has_price = any(term in lower for term in _PRICE_TERMS) or (
        "kemon" in lower and any(t in lower for t in ("dam", "দাম", "price", "টাকা"))
    )
    # "belt er dam" / "বেল্টের দাম"
    if _has_belt(lower) and (
        has_price or "kemon" in lower or "কত" in lower or "কেমন" in lower
    ):
        return True
    # Short follow-up only if the recent user turn was about a belt.
    if has_price and len(lower) < 40 and _recent_user_mentions_belt(history):
        return True
    return False


def is_belt_supplier_query(text: str) -> bool:
    """Farmer explicitly asks where to buy a V-belt."""
    lower = (text or "").lower()
    if not _has_belt(lower):
        return False
    if any(term in lower for term in _ACQUIRE_TERMS + _DEALER_NOUNS):
        return True
    # A bare "বেল্ট কোথায়?" is a shopping question; the same words inside a longer
    # sentence are usually part of a different question.
    return len(lower) <= 24 and any(term in lower for term in _SHOP_CONTEXT_TERMS)


def clearly_needs_new_belt(user_text: str, reply_text: str) -> bool:
    """True only when buy/replace intent is explicit — not every belt fault."""
    blob = f"{user_text or ''}\n{reply_text or ''}".lower()
    if not _has_belt(blob):
        return False
    return any(term in blob for term in _BUY_OR_REPLACE_TERMS)


def should_include_belt_dealers(
    user_text: str,
    reply_text: str,
    history: list[dict[str, str]] | None = None,
) -> bool:
    """Dealers only for: where-to-buy, price, or clear new-belt need."""
    from app.utils.reply_metadata import strip_leaked_metadata

    reply_text = strip_leaked_metadata(reply_text)
    if is_belt_price_query(user_text, history):
        return True
    if is_belt_supplier_query(user_text):
        return True
    if clearly_needs_new_belt(user_text, reply_text):
        return True
    return False


def should_skip_belt_images(
    user_text: str,
    history: list[dict[str, str]] | None = None,
) -> bool:
    """No gallery for belt price / where-to-buy."""
    from app.services.reference_selector import build_image_selection_query

    query = build_image_selection_query(user_text or "", history)
    return is_belt_price_query(query, history) or is_belt_supplier_query(query)


def _belt_dealers() -> list[dict]:
    kb = get_knowledge_base()
    block = kb.machine_data.get("parts_suppliers", {}).get("v_belt_b65", {})
    return block.get("dealers") or []


def _dealers_complete(text: str) -> bool:
    """Every verified dealer's mobile number is already in the reply."""
    dealers = _belt_dealers()
    if not dealers:
        return False
    return all(
        (d.get("mobile_bn") or d.get("mobile") or "") in text for d in dealers
    )


def _reply_looks_truncated(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    if t.endswith((".", "।", "!", "?", ":", ")", "»", "”", '"', "’", "'")):
        return False
    if t.count("(") > t.count(")"):
        return True
    if re.search(r"\d+\s*(mm|mim|মিমি)?$", t, re.I):
        return True
    return False


def _format_dealer_lines(dealers: list[dict]) -> list[str]:
    lines: list[str] = []
    bn_digits = ("১", "২", "৩", "৪", "৫", "৬", "৭", "৮", "৯")

    for idx, dealer in enumerate(dealers, start=1):
        num = bn_digits[idx - 1] if idx <= len(bn_digits) else str(idx)
        name = dealer.get("name_bn") or dealer.get("name") or ""
        lines.append(f"{num}. {name}")
        point = dealer.get("dealer_point_bn") or dealer.get("address_bn")
        if point:
            label = "ডিলার পয়েন্ট" if dealer.get("dealer_point_bn") else "ঠিকানা"
            lines.append(f"   {label}: {point}")
        mobile_bn = dealer.get("mobile_bn") or dealer.get("mobile")
        if mobile_bn:
            lines.append(f"   মোবাইল: {mobile_bn}")
        maps_url = dealer.get("maps_url")
        if maps_url:
            lines.append(f"   গুগল ম্যাপ: {maps_url}")
        lines.append("")
    return lines


def format_belt_suppliers_bn(*, heading: str | None = None) -> str:
    dealers = _belt_dealers()

    if heading is not None:
        lines = [heading, ""] if heading else []
    else:
        lines = [
            "BRRI Winnower (model BRRI Win2024) মেশিনের B65 ভি-বেল্ট (১৬৫০ mm) "
            "নিচের অনুমোদিত ডিলার/দোকান থেকে পাওয়া যায়:",
            "",
        ]

    lines.extend(_format_dealer_lines(dealers))
    lines.append("বেল্টের গায়ে B65 মার্কিং আছে কিনা কেনার সময় দেখে নিন।")
    return "\n".join(lines).strip()


def format_belt_price_reply_bn() -> str:
    dealers = _belt_dealers()

    lines = [
        "B65 ভি-বেল্ট (১৬৫০ mm) এর দাম সময় ও বাজার অনুযায়ী বদলায়; "
        "আমাদের কাছে স্থায়ী মূল্য তালিকা নেই।",
        "",
        "বর্তমান দাম জানতে অনুমোদিত ডিলারে ফোন করুন:",
        "",
    ]
    lines.extend(_format_dealer_lines(dealers))
    lines.append("কেনার সময় বেল্টের গায়ে B65 মার্কিং আছে কিনা দেখে নিন।")
    return "\n".join(lines).strip()


def ensure_belt_dealers_in_reply(
    text: str,
    user_text: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    """Append dealers only when buy/price/replace is clearly intended."""
    from app.utils.reply_metadata import strip_leaked_metadata

    text = strip_leaked_metadata(text)

    if not should_include_belt_dealers(user_text, text, history):
        return text

    if is_belt_price_query(user_text, history):
        if _dealers_complete(text) and not _reply_looks_truncated(text):
            return text.strip()
        return format_belt_price_reply_bn()

    # Contact details already present: never append a second copy. A dealer line ending
    # in a phone number trips the truncation heuristic, and printing the same shop twice
    # is worse for the farmer than an abrupt ending.
    if _dealers_complete(text):
        return text.strip()

    if is_belt_supplier_query(user_text):
        # Append rather than replace, so a draft that answered something else as well
        # (say, whether a B-52 belt fits) is not thrown away.
        if len(text.strip()) < 40 or _reply_looks_truncated(text):
            return format_belt_suppliers_bn()
        return (
            f"{text.rstrip()}\n\n"
            f"{format_belt_suppliers_bn(heading='B65 বেল্ট কেনার জায়গা:')}"
        )

    # Clear new-belt need: append quietly under the diagnosis.
    return (
        f"{text.rstrip()}\n\n"
        f"{format_belt_suppliers_bn(heading='নতুন B65 বেল্ট লাগলে কেনার জায়গা:')}"
    )


ensure_belt_supplier_reply = ensure_belt_dealers_in_reply
