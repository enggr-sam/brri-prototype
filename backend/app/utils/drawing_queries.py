"""Detect when a user question needs CAD / sub-assembly technical drawings."""

from __future__ import annotations

_DRAWING_QUERY_MARKERS = (
    "cad",
    "drawing",
    "blueprint",
    "dimension",
    "cutting",
    "fabricat",
    "manufactur",
    "weld",
    "blacksmith",
    "measure",
    "mm",
    "plate",
    "pattern",
    "খসড়া",
    "মাপ",
    "অংক",
    "তৈরি",
    "ওয়েল্ড",
    "কামাই",
    "নকশা",
    "ড্রয়িং",
)


_ASSEMBLY_QUERY_MARKERS = (
    "sub-assembly",
    "sub assembly",
    "exploded",
    "how parts fit",
    "assembly diagram",
    "assembly drawing",
    "complete assembly",
    "full assembly",
    "exploded view",
    "bom",
    "bill of materials",
    "parts list",
    "connected",
    "connection",
    "কিভাবে লাগে",
    "যন্ত্রাংশ সাজ",
    "আলাদা করে",
    "অ্যাসেম্বলি",
    "এসেম্বলি",
    "এক্সপ্লোড",
    "সম্পূর্ণ ড্রয়িং",
    "সম্পূর্ণ নকশা",
)

_HOW_IT_WORKS_MARKERS = (
    "কীভাবে কাজ",
    "কিভাবে কাজ",
    "how does",
    "how it work",
    "how the winnower work",
    "ধাপে ধাপে",
    "step by step",
    "কাজ করে?",
    "কাজ করে।",
)


def query_wants_technical_drawing(text: str) -> bool:
    """True when the farmer/mechanic asks for dimensions, fabrication, or assembly layout."""
    lower = (text or "").lower()
    return any(m in lower for m in _DRAWING_QUERY_MARKERS)


def query_wants_assembly_diagram(text: str) -> bool:
    lower = (text or "").lower()
    return any(t in lower for t in _ASSEMBLY_QUERY_MARKERS)


def query_is_how_it_works(text: str) -> bool:
    """How the machine works — show hopper + drive, not a random motor crop."""
    lower = (text or "").lower()
    return any(t in lower for t in _HOW_IT_WORKS_MARKERS)
