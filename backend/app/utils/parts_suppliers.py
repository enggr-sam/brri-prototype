"""Detect belt-buying / belt-replacement context and inject canonical dealer info."""

from __future__ import annotations

from app.services.knowledge_base import get_knowledge_base

_BELT_TERMS = ("belt", "বেল্ট", "b65", "v-belt", "v belt", "ভি-বেল্ট", "ভি বেল্ট")

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
    "কিন",
    "পাওয়া যায়",
    "পাবেন",
    "ডিলার",
)


def is_belt_supplier_query(text: str) -> bool:
    """Farmer explicitly asks where to buy a V-belt."""
    lower = (text or "").lower()
    has_belt = any(term in lower for term in _BELT_TERMS)
    wants_source = any(term in lower for term in _SUPPLIER_TERMS)
    return has_belt and wants_source


def is_belt_fault_context(text: str) -> bool:
    """Belt problem report (slip, crack, broken, etc.)."""
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
    if is_belt_supplier_query(user_text):
        return True
    if is_belt_fault_context(user_text):
        return True
    if reply_suggests_belt_replacement(reply_text):
        return True
    return False


def _dealers_complete(text: str) -> bool:
    return "০১৭১৮২৩২৪০৬" in text and "০১৭১৮২৩১৪৯৬" in text


def format_belt_suppliers_bn(*, heading: str | None = None) -> str:
    """Canonical Bangla dealer list with Google Maps links."""
    kb = get_knowledge_base()
    block = kb.machine_data.get("parts_suppliers", {}).get("v_belt_b65", {})
    dealers = block.get("dealers") or []

    if heading:
        lines = [heading, ""]
    else:
        lines = [
            "বিআরআরআই উইনোয়ার ২০২৪ (BRRI Win2024) মেশিনের B65 ভি-বেল্ট (১৬৫০ mm) "
            "নিচের অনুমোদিত ডিলার/দোকান থেকে পাওয়া যায়:",
            "",
        ]

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

    lines.append("বেল্টের গায়ে B65 মার্কিং আছে কিনা কেনার সময় দেখে নিন।")
    return "\n".join(lines).strip()


def ensure_belt_dealers_in_reply(text: str, user_text: str) -> str:
    """Ensure approved B65 belt dealers (with maps) appear when relevant."""
    if not should_include_belt_dealers(user_text, text):
        return text
    if _dealers_complete(text):
        return text.strip()
    if is_belt_supplier_query(user_text):
        return format_belt_suppliers_bn()
    return f"{text.rstrip()}\n\n{format_belt_suppliers_bn(heading='নতুন B65 বেল্ট কেনার জায়গা:')}"


# Backwards-compatible alias
ensure_belt_supplier_reply = ensure_belt_dealers_in_reply
