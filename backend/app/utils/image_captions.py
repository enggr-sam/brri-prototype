"""Parse per-image contextual notes for the reference gallery."""

import re
from pathlib import Path

from app.services.knowledge_base import get_knowledge_base
from app.utils.image_labels import display_label

_CAPTION_LINE = re.compile(r"^IMG#(\d+):\s*(.+)$", re.IGNORECASE)


def parse_image_caption_lines(text: str) -> dict[int, str]:
    """Extract IMG# lines from a caption-only model response."""
    captions: dict[int, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = _CAPTION_LINE.match(stripped)
        if match:
            captions[int(match.group(1))] = match.group(2).strip()
    return captions


def caption_prompt(
    user_text: str,
    reply: str,
    reference_images: list[Path],
) -> str:
    kb = get_knowledge_base()
    photo_lines: list[str] = []
    for path in reference_images:
        entry = kb._by_name.get(path.name, {})
        num = entry.get("image_number")
        if num is None:
            continue
        label = display_label(entry, path.name)
        desc = entry.get("description") or ""
        hook = desc.split("Troubleshooting context:", 1)[-1].strip() if desc else ""
        photo_lines.append(f"- ছবি #{num} ({label}): {hook[:160]}")

    return (
        "কৃষকের সমস্যা:\n"
        f"{user_text.strip()}\n\n"
        "আপনার দেওয়া সমাধান:\n"
        f"{reply.strip()[:700]}\n\n"
        "প্রতিটি রেফারেন্স ছবির নিচে দেখানোর জন্য ২–৩ সম্পূর্ণ বাংলা বাক্য লিখুন — "
        "এই ছবি কেন দেখাচ্ছেন, কৃষকের সমস্যায় কী তুলনা করবেন, কী করলে ঠিক হবে।\n"
        "শুধু এই ফরম্যাটে উত্তর দিন (প্রতি ছবি এক লাইন):\n"
        "IMG#<নম্বর>: <বাংলা ব্যাখ্যা>\n\n"
        "ছবি:\n" + "\n".join(photo_lines)
    )
