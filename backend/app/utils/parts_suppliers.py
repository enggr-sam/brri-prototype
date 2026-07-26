"""Detect parts-buying questions and return canonical dealer text from machine_data."""

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


def is_belt_supplier_query(text: str) -> bool:
    """True when the farmer asks where to buy / get a V-belt (not a fault report)."""
    lower = (text or "").lower()
    has_belt = any(term in lower for term in _BELT_TERMS)
    wants_source = any(term in lower for term in _SUPPLIER_TERMS)
    return has_belt and wants_source


def _dealers_complete(text: str) -> bool:
    return "০১৭১৮২৩২৪০৬" in text and "০১৭১৮২৩১৪৯৬" in text


def format_belt_suppliers_bn() -> str:
    """Canonical Bangla reply — always lists both approved B65 belt dealers."""
    kb = get_knowledge_base()
    block = kb.machine_data.get("parts_suppliers", {}).get("v_belt_b65", {})
    dealers = block.get("dealers") or []

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
        lines.append("")

    lines.append("বেল্টের গায়ে B65 মার্কিং আছে কিনা কেনার সময় দেখে নিন।")
    return "\n".join(lines).strip()


def ensure_belt_supplier_reply(text: str, user_text: str) -> str:
    """Replace incomplete model replies with the full dealer list when needed."""
    if not is_belt_supplier_query(user_text):
        return text
    if _dealers_complete(text):
        return text.strip()
    return format_belt_suppliers_bn()
