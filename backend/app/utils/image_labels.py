"""Bangla display labels for the in-app reference gallery.

The gallery used to caption images from their filenames, which produced things like
"Field 10" and "Subasm 33 10 Winnower Show Cover" — meaningless to a farmer. Every
image already carries a real part name in the collected data (``part_paper`` for field
photos, ``part_name`` for CAD, ``title`` for sub-assemblies); these maps turn those into
the Bangla wording the rest of the app already uses.

Bangla for the parts that appear in fault trees is taken from the collection form's own
``part_local_bn`` column; the rest use the standard shop terms found in prompts.txt.
"""

from __future__ import annotations

import re

_DRAWING_SUFFIX = "নকশা"

# Field photo part_paper → Bangla.
_FIELD_PART_BN: dict[str, str] = {
    "main frame": "মূল ফ্রেম",
    "hopper (front / back / bottom plate)": "হপার (সামনে/পেছনে/নিচের পাত)",
    "air control plate": "এয়ার কন্ট্রোল পাত",
    "grain control plate": "ধান নিয়ন্ত্রণ পাত (ফিড গেট)",
    "blower unite (assembled)": "ব্লোয়ার ইউনিট (পাখা)",
    "blower cover plate / fan opening": "ব্লোয়ার কভার পাত",
    "air outlet control plate": "বাতাস বের হওয়ার নিয়ন্ত্রণ পাত",
    "sieve (three type)": "ঝরনি জাল (তিন প্রকার)",
    "sieve shaft": "ঝরনি শ্যাফট",
    "power pulley belt (b65 marking visible)": "ভি-বেল্ট (B65 মার্কিং)",
    "motor": "মোটর",
    "motor pulley": "মোটর পুলি",
    "blower pulley": "ব্লোয়ার পুলি",
    "pillow bearing block- ucp206": "পিলো বিয়ারিং ব্লক (UCP206)",
    "ball bearing-6302": "বল বিয়ারিং (6302)",
    "bearing 6203 (sieve)": "বিয়ারিং 6203 (ঝরনি)",
    "grain outlet / grain outlet 2nd plate": "ধান বের হওয়ার মুখ ও দ্বিতীয় পাত",
    "winnower show cover": "শো কভার",
    "full machine front view": "পুরো মেশিন (সামনে থেকে)",
    "full machine side view": "পুরো মেশিন (পাশ থেকে)",
}

# CAD part_name → Bangla.
_CAD_PART_BN: dict[str, str] = {
    "base plate": "বেস প্লেট",
    "bearing support plate": "বিয়ারিং সাপোর্ট প্লেট",
    "blower side cover-1": "ব্লোয়ার সাইড কভার-১",
    "blower side cover -2": "ব্লোয়ার সাইড কভার-২",
    "blower cover": "ব্লোয়ার কভার",
    "blower front plate": "ব্লোয়ারের সামনের পাত",
    "blower plate": "ব্লোয়ার পাত",
    "dust cover": "ধুলা কভার",
    "dust delivery drain": "ধুলা বের হওয়ার পথ",
    "fan plate": "পাখার পাত",
    "air control plate": "এয়ার কন্ট্রোল পাত",
    "grain delivery gate": "ধান বের হওয়ার গেট",
    "grain divider-1": "ধান ভাগ করার পাত-১",
    "grain divider-2": "ধান ভাগ করার পাত-২",
    "grain control plate": "ধান নিয়ন্ত্রণ পাত",
    "hopper part-1": "হপারের অংশ-১",
    "hopper part-2": "হপারের অংশ-২",
    "zigzag plate": "জিগজ্যাগ পাত",
    "winnower left side": "মেশিনের বাম পাশ",
    "winnower right side": "মেশিনের ডান পাশ",
    "grain control gate": "ধান নিয়ন্ত্রণ গেট",
    "sieve frame-1": "ঝরনি ফ্রেম-১",
    "sieve frame-2": "ঝরনি ফ্রেম-২",
    "angle plate": "অ্যাঙ্গেল প্লেট",
    "sieve frame side part": "ঝরনি ফ্রেমের পাশের অংশ",
    "sieve small shaft": "ঝরনির ছোট শ্যাফট",
    "sieve top cover": "ঝরনির উপরের কভার",
    "winnower back cover": "মেশিনের পেছনের কভার",
    "winnower hopper bottom side": "হপারের নিচের দিক",
}

# Sub-assembly number (from titles like "2 — SIEVE") → Bangla.
_SUBASSEMBLY_BN: dict[str, str] = {
    "1": "মূল বডি — যন্ত্রাংশ তালিকা",
    "2": "ঝরনি অ্যাসেম্বলি",
    "3": "ব্লোয়ার ইউনিট",
    "4": "বিয়ারিং হাউস",
    "5": "ব্লোয়ার পুলি",
    "6": "পাওয়ার পুলি ও বেল্ট",
    "7": "মোটর",
    "8": "মোটর পুলি",
    "9": "ঝরনি শ্যাফট",
    "10": "শো কভার",
}

# Hand-curated photographs, keyed by image_number.
_CURATED_BN: dict[int, str] = {
    1: "মোটর পুলি ও বেল্ট সিস্টেম",
    2: "পুরো মেশিন (বাইরের দৃশ্য)",
    11: "হপারের ফিড গেট ও ঝরনি",
    13: "এয়ার কন্ট্রোল লিভার ও ঝরনি ড্রাইভ আর্ম",
    14: "ব্লোয়ারে বাতাস ঢোকার মুখ (খোলা)",
    20: "মোটরের নিচের পুলি",
    23: "মোটর মাউন্ট ও ফ্রেমের পা",
    24: "ঝরনির ধান বের হওয়ার মুখ",
    27: "ভি-বেল্ট B65 মার্কিং (কাছ থেকে)",
    28: "ঝরনির জাল (উপর থেকে)",
    29: "হপারের ফিড গেট (কাছ থেকে)",
    30: "ঝরনি ড্রাইভ আর্ম ও পিলো বিয়ারিং",
    31: "ঝরনির ক্র্যাঙ্ক ও পিলো বিয়ারিং",
    32: "পেছনের দিক — চিটা বের হওয়ার মুখ ও ঝরনি শ্যাফট",
    33: "ব্লোয়ার পুলি ও ঝরনির লিঙ্ক আর্ম",
    34: "ঝরনির কানেক্টিং রড (ছোট)",
    36: "ঝরনির কানেক্টিং রড (বড়)",
}


def _norm(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _lookup(table: dict[str, str], raw: str | None) -> str | None:
    key = _norm(raw)
    if not key:
        return None
    if key in table:
        return table[key]
    # Retry without a trailing qualifier, e.g. "motor (assembled)" → "motor".
    stripped = _norm(re.sub(r"\([^)]*\)", "", key))
    return table.get(stripped)


def _english_fallback(raw: str | None) -> str | None:
    """Readable English part name — still far better than a filename."""
    cleaned = re.sub(r"\s+", " ", (raw or "").strip())
    return cleaned.title() if cleaned else None


def _label_from_filename(image_name: str) -> str:
    name = image_name
    if "_" in name and name[:2].isdigit():
        name = name.split("_", 1)[1]
    return name.rsplit(".", 1)[0].replace("_", " ").title()


def display_label(entry: dict, image_name: str) -> str:
    """Bangla caption for one gallery image."""
    source = entry.get("source") or "curated"

    if source == "field_collection":
        part = entry.get("part_paper")
        return (
            _lookup(_FIELD_PART_BN, part)
            or _english_fallback(part)
            or _label_from_filename(image_name)
        )

    if source == "cad_drawing":
        part = entry.get("part_name")
        label = _lookup(_CAD_PART_BN, part) or _english_fallback(part)
        return f"{label} ({_DRAWING_SUFFIX})" if label else _label_from_filename(image_name)

    if source == "subassembly_drawing":
        # Sub-assembly files are photos of the real part. Do not add (নকশা) —
        # that suffix is only for CAD cutting drawings.
        title = entry.get("title") or ""
        number = title.split("—")[0].strip() if "—" in title else ""
        label = _SUBASSEMBLY_BN.get(number)
        if not label:
            label = _english_fallback(title.split("—")[-1])
        return label or _label_from_filename(image_name)

    number = entry.get("image_number")
    if isinstance(number, int) and number in _CURATED_BN:
        return _CURATED_BN[number]
    return _label_from_filename(image_name)
