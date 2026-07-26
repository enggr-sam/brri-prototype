"""Detect belt-buying / belt-replacement context and inject canonical dealer info."""

from __future__ import annotations

import re

from app.services.knowledge_base import get_knowledge_base

_BELT_TERMS = ("belt", "বেল্ট", "b65", "v-belt", "v belt", "ভি-বেল্ট", "ভি বেল্ট")

_PRICE_TERMS = (
    "price",
    "dam",
    "দাম",
    "মূল্য",
    "koto",
    "কত",
    "টাকা",
    "kemon",
    "cost",
    "rate",
)

_SUPPLIER_TERMS = (
    "কোথায়",
    "কোথায়",
    "kothai",
    "kothay",
    "where",
    "পাব",
    "পাও",
    "pawa",
    "paowa",
    "jabe",
    "যাবে",
    "kinbo",
    "কিনব",
    "buy",
    "ডিলার",
    "dealer",
    "দোকান",
    "supplier",
    "shop",
    "vendor",
)

_BELT_FAULT_TERMS = (
    "slip",
    "slipping",
    "crack",
    "cracked",
    "broken",
    "tear",
    "torn",
    "worn",
    "replace",
    "loose",
    "cut",
    "damage",
    "পিছল",
    "ছিঁড়",
    "ছিড়",
    "ভাঙ",
    "আলগা",
    "ঝুল",
    "নতুন বেল্ট",
    "বেল্ট বদল",
    "tension",
    "তেনশন",
)

_REPLACEMENT_REPLY_TERMS = (
    "নতুন বেল্ট",
    "বেল্ট বদল",
    "বদলে",
    "replace",
    "replacement",
    "ছিঁড়",
    "ছিড়",
    "crack",
    "broken",
    "ভাঙ",
    "পাওয়া যায়",
    "পাবেন",
)


def is_belt_price_query(text: str) -> bool:
    """Farmer asks belt price (দাম, price kemon, etc.)."""
    lower = (text or "").lower().strip()
    if not lower:
        return False
    has_price = any(term in lower for term in _PRICE_TERMS)
    has_belt = any(term in lower for term in _BELT_TERMS)
    if has_belt and has_price:
        return True
    # Short follow-up: "price kemon?" after a belt message in the same session.
    if has_price and len(lower) < 40:
        return True
    return False


def is_belt_supplier_query(text: str) -> bool:
    """Farmer explicitly asks where to buy a V-belt."""
    lower = (text or "").lower()
    if is_belt_price_query(text):
        return False
    has_belt = any(term in lower for term in _BELT_TERMS)
    wants_source = any(term in lower for term in _SUPPLIER_TERMS)
    return has_belt and wants_source


def is_belt_fault_context(text: str) -> bool:
    """Belt problem report (slip, crack, broken, etc.)."""
    if is_belt_price_query(text):
        return False
    lower = (text or "").lower()
    if not any(term in lower for term in _BELT_TERMS):
        return False
    return any(term in lower for term in _BELT_FAULT_TERMS)


def reply_suggests_belt_replacement(text: str) -> bool:
    """Assistant reply indicates a new belt may be needed."""
    lower = (text or "").lower()
    if not any(term in lower for term in _BELT_TERMS):
        return False
    return any(term in lower for term in _REPLACEMENT_REPLY_TERMS)


def should_include_belt_dealers(user_text: str, reply_text: str) -> bool:
    from app.utils.reply_metadata import strip_leaked_metadata

    reply_text = strip_leaked_metadata(reply_text)
    if is_belt_price_query(user_text):
        return True
    if is_belt_supplier_query(user_text):
        return True
    if is_belt_fault_context(user_text):
        return True
    if reply_suggests_belt_replacement(reply_text):
        return True
    return False


def should_skip_belt_images(user_text: str, history: list[dict[str, str]] | None = None) -> bool:
    """No reference gallery for price / where-to-buy belt questions."""
    from app.services.reference_selector import build_image_selection_query

    query = build_image_selection_query(user_text or "", history)
    return is_belt_price_query(query) or is_belt_supplier_query(query)


def _dealers_complete(text: str) -> bool:
    return "০১৭১৮২৩২৪০৬" in text and "০১৭১৮২৩১৪৯৬" in text


def _reply_looks_truncated(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    if t.endswith((".", "।", "!", "?", ":", ")", "»", "”", '"', "’", "'")):
        return False
    # Unclosed parenthesis / cut mid-spec.
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
    """Canonical Bangla dealer list with Google Maps links."""
    kb = get_knowledge_base()
    block = kb.machine_data.get("parts_suppliers", {}).get("v_belt_b65", {})
    dealers = block.get("dealers") or []

    if heading is not None:
        lines = [heading, ""] if heading else []
    else:
        lines = [
            "বিআরআরআই উইনোয়ার ২০২৪ (BRRI Win2024) মেশিনের B65 ভি-বেল্ট (১৬৫০ mm) "
            "নিচের অনুমোদিত ডিলার/দোকান থেকে পাওয়া যায়:",
            "",
        ]

    lines.extend(_format_dealer_lines(dealers))
    lines.append("বেল্টের গায়ে B65 মার্কিং আছে কিনা কেনার সময় দেখে নিন।")
    return "\n".join(lines).strip()


def format_belt_price_reply_bn() -> str:
    """Price varies — direct farmer to dealers (no fixed price in KB)."""
    kb = get_knowledge_base()
    dealers = kb.machine_data.get("parts_suppliers", {}).get("v_belt_b65", {}).get("dealers") or []

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


def ensure_belt_dealers_in_reply(text: str, user_text: str) -> str:
    """Ensure approved B65 belt dealers (with maps) appear when relevant."""
    from app.utils.reply_metadata import strip_leaked_metadata

    text = strip_leaked_metadata(text)

    if not should_include_belt_dealers(user_text, text):
        return text

    if is_belt_price_query(user_text):
        if _dealers_complete(text) and not _reply_looks_truncated(text) and "দাম" in text:
            return text.strip()
        return format_belt_price_reply_bn()

    if _dealers_complete(text) and not _reply_looks_truncated(text):
        return text.strip()

    if is_belt_supplier_query(user_text):
        return format_belt_suppliers_bn()

    if _reply_looks_truncated(text):
        return format_belt_suppliers_bn(
            heading="নতুন B65 বেল্ট কেনার জায়গা:"
        )

    return f"{text.rstrip()}\n\n{format_belt_suppliers_bn(heading='নতুন B65 বেল্ট কেনার জায়গা:')}"


ensure_belt_supplier_reply = ensure_belt_dealers_in_reply
