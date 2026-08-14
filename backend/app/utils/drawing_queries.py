"""Detect when a user question needs CAD / sub-assembly technical drawings."""

from __future__ import annotations

_DRAWING_QUERY_MARKERS = (
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


def query_wants_technical_drawing(text: str) -> bool:
    """True when the farmer/mechanic asks for dimensions, fabrication, or assembly layout."""
    lower = (text or "").lower()
    return any(m in lower for m in _DRAWING_QUERY_MARKERS)


def query_wants_assembly_diagram(text: str) -> bool:
    lower = (text or "").lower()
    assembly_terms = (
        "sub-assembly",
        "sub assembly",
        "exploded",
        "how parts fit",
        "assembly diagram",
        "কিভাবে লাগে",
        "যন্ত্রাংশ সাজ",
        "আলাদা করে",
        "exploded view",
        "bom",
        "parts list",
    )
    return any(t in lower for t in assembly_terms)
