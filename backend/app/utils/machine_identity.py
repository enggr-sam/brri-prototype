"""Canonical farmer-facing machine name."""

from __future__ import annotations

from app.services.knowledge_base import get_knowledge_base

EN = "BRRI Multicrop Winnower"
BN = "ব্রি শস্য ঝাড়াই যন্ত্র"
MODEL = "BRRI Win2024"

_FORBIDDEN_BN = (
    "ব্রি উইনোয়ার",
    "ব্রি উইনোয়ার",
    "বিআরআরআই উইনোয়ার",
    "বিআরআরআই উইনোয়ার",
    "ব্রি ধান গম ঝাড়াই যন্ত্র",
    "ব্রি ধান গম ঝাড়াই যন্ত্র",
)


def names(data: dict | None = None) -> tuple[str, str, str]:
    src = data if data is not None else get_knowledge_base().machine_data
    return (
        src.get("machine_name") or EN,
        src.get("machine_name_bn") or BN,
        src.get("model") or src.get("short_name") or MODEL,
    )


def mention(data: dict | None = None) -> str:
    """Bangla name first, English + model in parentheses."""
    en, bn, model = names(data)
    return f"{bn} ({en}, Model: {model})"


def strip_forbidden_names(text: str) -> str:
    """Replace leftover old names in a reply."""
    if not text:
        return text
    out = text
    en, bn, model = names()
    for bad in _FORBIDDEN_BN:
        out = out.replace(bad, bn)
    out = out.replace("BRRI Winnower 2024", f"{en} ({model})")
    out = out.replace("BRRI Winnower", en)
    out = out.replace(f"{bn} ২০২৪", bn)
    out = out.replace(f"{bn} 2024", bn)
    return out
