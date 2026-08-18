"""Rich context for CAD cutting drawings and sub-assembly diagrams (BRRI Win2024).

Used by ``import_collected_data.py`` to build searchable catalogue entries and by
the backend to match farmer/mechanic questions to the right technical drawing.
"""

from __future__ import annotations

import re

# subsystem → common query terms (English + Bangla)
_SUBSYSTEM_KEYWORDS: dict[str, tuple[str, ...]] = {
    "main_frame": ("main frame", "frame", "base", "structure", "ফ্রেম", "বেস"),
    "hopper": ("hopper", "feed", "grain inlet", "হপার", "ঢালা", "দানা ঢাল"),
    "blower": ("blower", "fan", "air blast", "wind", "ব্লোয়ার", "পাখা", "বাতাস"),
    "sieve": ("sieve", "screen", "mesh", "oscillat", "ঝরন", "চালুনি", "জাল"),
    "grain_control": ("grain control", "feed gate", "flow", "গেট", "ফিড", "ধান প্রবাহ"),
    "air_control": ("air control", "wind speed", "airflow", "এয়ার", "বাতাস নিয়ন্ত্রণ"),
    "discharge": ("outlet", "discharge", "chute", "grain exit", "নল", "আউটলেট"),
    "winnower_body": ("winnower", "cover", "casing", "shell", "কভার", "গায়"),
}

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


def drawing_query_markers() -> tuple[str, ...]:
    return _DRAWING_QUERY_MARKERS


def _kw(*terms: str) -> list[str]:
    return list(terms)


# Normalised part name (lower) → metadata
CAD_PARTS: dict[str, dict] = {
    "base plate": {
        "subsystem": "main_frame",
        "keywords": _kw("base plate", "main frame bottom", "foundation plate", "বেস প্লেট"),
        "field_photo_no": "01",
        "description": (
            "CAD cutting drawing: BASE PLATE — bottom structural plate of the main frame. "
            "Flat-pattern dimensions for plain carbon steel; weld this first when rebuilding the machine body."
        ),
    },
    "bearing support plate": {
        "subsystem": "sieve",
        "keywords": _kw("bearing support", "support plate", "6203", "shaft mount", "বিয়ারিং সাপোর্ট"),
        "field_photo_no": "09",
        "description": (
            "CAD cutting drawing: BEARING SUPPORT PLATE — mounts sieve-shaft bearings (6203). "
            "Check if sieve oscillation failed due to cracked support or wrong hole spacing."
        ),
    },
    "blower side cover-1": {
        "subsystem": "blower",
        "keywords": _kw("blower side cover", "blower cover 1", "fan housing", "ব্লোয়ার কভার"),
        "field_photo_no": "05",
        "description": "CAD cutting drawing: BLOWER SIDE COVER-1 — left/right side panel of the blower unit housing.",
    },
    "blower side cover -2": {
        "subsystem": "blower",
        "keywords": _kw("blower side cover 2", "blower panel", "ব্লোয়ার পাশ"),
        "field_photo_no": "05",
        "description": "CAD cutting drawing: BLOWER SIDE COVER-2 — paired side panel for the blower unite assembly.",
    },
    "blower cover": {
        "subsystem": "blower",
        "keywords": _kw("blower cover", "fan cover", "blower lid", "ব্লোয়ার ঢাকনা"),
        "field_photo_no": "06",
        "description": (
            "CAD cutting drawing: BLOWER COVER — top/rear cover over the fan blades. "
            "Remove this to inspect blades or clear blockage inside the blower."
        ),
    },
    "blower front plate": {
        "subsystem": "blower",
        "keywords": _kw("blower front", "air intake", "fan opening", "ব্লোয়ার সামনে"),
        "field_photo_no": "06",
        "description": "CAD cutting drawing: BLOWER FRONT PLATE — front face of blower with air intake opening.",
    },
    "blower plate": {
        "subsystem": "blower",
        "keywords": _kw("blower plate", "fan plate", "impeller plate", "ব্লোয়ার প্লেট"),
        "field_photo_no": "05",
        "description": "CAD cutting drawing: BLOWER PLATE — internal plate within the blower unite sub-assembly.",
    },
    "dust cover": {
        "subsystem": "discharge",
        "keywords": _kw("dust cover", "dust hood", "chaff guard", "ধুল ঢাকনা", "তুষ"),
        "description": "CAD cutting drawing: DUST COVER — shields the dust/chaff discharge path from spillage.",
    },
    "dust delivery drain": {
        "subsystem": "discharge",
        "keywords": _kw("dust drain", "chaff outlet", "waste chute", "তুষ নল", "ধুল নিষ্কাশন"),
        "description": "CAD cutting drawing: DUST DELIVERY DRAIN — chute where chaff and light waste exit the machine.",
    },
    "fan plate": {
        "subsystem": "blower",
        "keywords": _kw("fan plate", "blade plate", "impeller", "পাখা প্লেট"),
        "field_photo_no": "05",
        "description": (
            "CAD cutting drawing: FAN PLATE — curved blade segment for the blower fan. "
            "Weak air may mean damaged or missing fan plates."
        ),
    },
    "air control plate": {
        "subsystem": "air_control",
        "keywords": _kw(
            "air control plate", "air control", "wind control", "airflow",
            "এয়ার কন্ট্রোল", "বাতাস কম", "বাতাস বেশি",
        ),
        "field_photo_no": "03",
        "description": (
            "CAD cutting drawing: AIR CONTROL PLATE — sliding plate that restricts blower airflow. "
            "If good grain blows away with chaff, this plate should be adjusted to reduce wind."
        ),
    },
    "grain delivery gate": {
        "subsystem": "grain_control",
        "keywords": _kw("grain delivery gate", "delivery gate", "feed opening", "দানা গেট"),
        "field_photo_no": "04",
        "description": "CAD cutting drawing: GRAIN DELIVERY GATE — controls grain flow from hopper onto the sieve.",
    },
    "grain divider-1": {
        "subsystem": "hopper",
        "keywords": _kw("grain divider", "divider 1", "hopper baffle", "বিভাজক"),
        "description": "CAD cutting drawing: GRAIN DIVIDER-1 — internal hopper baffle splitting grain flow evenly.",
    },
    "grain divider-2": {
        "subsystem": "hopper",
        "keywords": _kw("grain divider 2", "hopper divider", "বিভাজক"),
        "description": "CAD cutting drawing: GRAIN DIVIDER-2 — paired baffle inside the hopper assembly.",
    },
    "grain control plate": {
        "subsystem": "grain_control",
        "keywords": _kw(
            "grain control plate", "feed control", "green gate", "flow plate",
            "গ্রেন কন্ট্রোল", "ফিড গেট", "সবুজ গেট",
        ),
        "field_photo_no": "04",
        "description": (
            "CAD cutting drawing: GRAIN CONTROL PLATE — adjustable plate regulating how fast grain "
            "drops onto the sieve. Jamming or uneven feed often involves this part."
        ),
    },
    "hopper part-1": {
        "subsystem": "hopper",
        "keywords": _kw("hopper part 1", "hopper plate", "hopper side", "হপার"),
        "field_photo_no": "02",
        "description": "CAD cutting drawing: HOPPER PART-1 — first section of the grain intake hopper walls.",
    },
    "hopper part-2": {
        "subsystem": "hopper",
        "keywords": _kw("hopper part 2", "hopper back", "hopper bottom", "হপার"),
        "field_photo_no": "02",
        "description": "CAD cutting drawing: HOPPER PART-2 — remaining hopper panel(s) completing the intake bin.",
    },
    "zigzag plate": {
        "subsystem": "sieve",
        "keywords": _kw("zigzag", "zig zag", "baffle plate", "corrugated", "জিগজ্যাগ"),
        "description": (
            "CAD cutting drawing: ZIGZAG PLATE — corrugated deflector above the sieve bed; "
            "spreads grain evenly before screening."
        ),
    },
    "winnower left side": {
        "subsystem": "winnower_body",
        "keywords": _kw("left side", "winnower side", "side panel", "বাম পাশ"),
        "description": "CAD cutting drawing: WINNOWER LEFT SIDE — outer left skin panel of the machine body.",
    },
    "winnower right side": {
        "subsystem": "winnower_body",
        "keywords": _kw("right side", "winnower side", "side panel", "ডান পাশ"),
        "description": "CAD cutting drawing: WINNOWER RIGHT SIDE — outer right skin panel of the machine body.",
    },
    "grain control gate": {
        "subsystem": "grain_control",
        "keywords": _kw("grain control gate", "sliding gate", "feed gate", "গেট"),
        "field_photo_no": "04",
        "description": "CAD cutting drawing: GRAIN CONTROL GATE — sliding gate variant for feed-rate adjustment.",
    },
    "sieve frame-1": {
        "subsystem": "sieve",
        "keywords": _kw("sieve frame", "sieve frame 1", "screen frame", "ঝরন ফ্রেম", "চালুনি ফ্রেম"),
        "field_photo_no": "08",
        "description": (
            "CAD cutting drawing: SIEVE FRAME-1 — primary structural frame holding the perforated sieve net. "
            "Three sieve types (large / medium / small hole nets) mount in this frame."
        ),
    },
    "sieve frame-2": {
        "subsystem": "sieve",
        "keywords": _kw("sieve frame 2", "screen support", "ঝরন ফ্রেম"),
        "field_photo_no": "08",
        "description": "CAD cutting drawing: SIEVE FRAME-2 — secondary frame member for the oscillating sieve assembly.",
    },
    "angle plate": {
        "subsystem": "sieve",
        "keywords": _kw("angle plate", "angle iron", "bracket", "অ্যাঙ্গেল"),
        "field_photo_no": "08",
        "description": "CAD cutting drawing: ANGLE PLATE — angled bracket reinforcing the sieve frame joints.",
    },
    "sieve frame side part": {
        "subsystem": "sieve",
        "keywords": _kw("sieve side", "frame side", "sieve bracket", "ঝরন পাশ"),
        "field_photo_no": "08",
        "description": "CAD cutting drawing: SIEVE FRAME SIDE PART — side bracket linking sieve frame to the main body.",
    },
    "sieve small shaft": {
        "subsystem": "sieve",
        "keywords": _kw("sieve shaft", "small shaft", "oscillating shaft", "ঝরন শ্যাফট", "শ্যাফট"),
        "field_photo_no": "09",
        "description": (
            "CAD cutting drawing: SIEVE SMALL SHAFT — short shaft driving sieve oscillation. "
            "If sieve does not shake, inspect this shaft and its 6203 bearings."
        ),
    },
    "sieve top cover": {
        "subsystem": "sieve",
        "keywords": _kw("sieve cover", "top cover", "screen cover", "ঝরন ঢাকনা"),
        "field_photo_no": "08",
        "description": "CAD cutting drawing: SIEVE TOP COVER — cover plate over the vibrating sieve bed.",
    },
    "winnower back cover": {
        "subsystem": "winnower_body",
        "keywords": _kw("back cover", "rear cover", "winnower back", "পেছনের ঢাকনা"),
        "field_photo_no": "18",
        "description": "CAD cutting drawing: WINNOWER BACK COVER — rear access panel of the winnower shell.",
    },
    "winnower hopper bottom side": {
        "subsystem": "hopper",
        "keywords": _kw("hopper bottom", "bottom plate", "hopper outlet", "হপার নিচ"),
        "field_photo_no": "02",
        "description": "CAD cutting drawing: WINNOWER HOPPER BOTTOM SIDE — bottom/side panel where hopper meets the sieve.",
    },
}


SUBASSEMBLIES: dict[str, dict] = {
    "1 — main body (bom)": {
        "subsystem": "main_frame",
        "keywords": _kw("main body", "bom", "bill of materials", "main frame", "assembly 1", "মূল দেহ"),
        "description": (
            "Sub-assembly diagram 1 — MAIN BODY (BOM): exploded view + parts table for frame, hopper, "
            "air control plate, sieve, grain outlets. Start here for overall machine layout."
        ),
    },
    "2 — sieve": {
        "subsystem": "sieve",
        "keywords": _kw("sub assembly 2", "sieve assembly", "6203", "three sieve", "ঝরনি", "sub-assembly 2"),
        "field_photo_no": "08",
        "description": (
            "Sub-assembly diagram 2 — SIEVE: shows 6203×2 bearings, three sieve types, "
            "frame and mounting. Use when farmer asks how sieve parts fit together."
        ),
    },
    "3 — blower unite": {
        "subsystem": "blower",
        "keywords": _kw("blower unite", "blower unit", "blower assembly", "fan assembly", "sub-assembly 3"),
        "field_photo_no": "05",
        "description": (
            "Sub-assembly diagram 3 — BLOWER UNITE: 12-part exploded fan assembly "
            "(shaft, bearings, side covers, fan plates). For weak air or blower repair."
        ),
    },
    "4 — bearing house": {
        "subsystem": "blower",
        "keywords": _kw("bearing house", "bearing housing", "pillow block", "ucp206", "sub-assembly 4"),
        "field_photo_no": "14",
        "description": (
            "Sub-assembly diagram 4 — BEARING HOUSE: blower shaft pillow bearing mounting. "
            "Links to UCP206 bearing replacement."
        ),
    },
    "5 — blower pulley": {
        "subsystem": "pulley",
        "keywords": _kw("blower pulley", "upper pulley", "cast pulley", "sub-assembly 5"),
        "field_photo_no": "13",
        "description": "Sub-assembly diagram 5 — BLOWER PULLEY: large cast-iron pulley on the blower shaft.",
    },
    "6 — power pulley belt": {
        "subsystem": "belt",
        "keywords": _kw("power pulley belt", "v-belt", "b65", "belt drive", "sub-assembly 6"),
        "field_photo_no": "10",
        "description": (
            "Sub-assembly diagram 6 — POWER PULLEY BELT: B-type belt 65 inch connecting motor to blower pulley."
        ),
    },
    "7 — motor": {
        "subsystem": "motor",
        "keywords": _kw("motor assembly", "1.5 hp", "1.1 kw", "1400 rpm", "sub-assembly 7"),
        "field_photo_no": "11",
        "description": (
            "Sub-assembly diagram 7 — MOTOR: 1.5 HP / 1.1 kW / 1400 rpm single-phase motor mounting."
        ),
    },
    "8 — motor pulley": {
        "subsystem": "pulley",
        "keywords": _kw("motor pulley", "small pulley", "drive pulley", "sub-assembly 8"),
        "field_photo_no": "12",
        "description": "Sub-assembly diagram 8 — MOTOR PULLEY: pulley on motor shaft; sets belt speed ratio.",
    },
    "9 — sieve shaft": {
        "subsystem": "sieve",
        "keywords": _kw("sieve shaft assembly", "crank", "connecting rod", "sub-assembly 9"),
        "field_photo_no": "09",
        "description": (
            "Sub-assembly diagram 9 — SIEVE SHAFT: crank/linkage driving sieve oscillation. "
            "Use when sieve stops shaking — check bearings and connecting bolts."
        ),
    },
    "10 — winnower show cover": {
        "subsystem": "winnower_body",
        "keywords": _kw("show cover", "display cover", "outer cover", "sub-assembly 10"),
        "field_photo_no": "18",
        "description": (
            "Sub-assembly diagram 10 — WINNOWER SHOW COVER (qty 2): outer cosmetic/ protective covers."
        ),
    },
}


def lookup_cad_part(part_name: str) -> dict:
    """Return metadata for a CAD part name (case-insensitive, fuzzy dash/spacing)."""
    key = (part_name or "").strip().lower()
    key = re.sub(r"\s+", " ", key)
    if key in CAD_PARTS:
        return CAD_PARTS[key]
    key2 = key.replace(" -", "-").replace("- ", "-")
    return CAD_PARTS.get(key2, {})


def lookup_subassembly(title: str) -> dict:
    key = (title or "").strip().lower()
    return SUBASSEMBLIES.get(key, {})


def subsystem_keywords(subsystem: str) -> tuple[str, ...]:
    return _SUBSYSTEM_KEYWORDS.get(subsystem, ())
