"""Detect incomplete drafts and build a Q&A polish prompt for a complete reply."""

from __future__ import annotations

import re

from app.utils.reply_metadata import strip_leaked_metadata

_END_OK = (".", "।", "!", "?", "…", ")", "」", "”", '"', "’", "'")


def looks_incomplete(text: str) -> bool:
    """True if the draft looks cut off mid-sentence / mid-word / mid-list."""
    t = strip_leaked_metadata(text or "").strip()
    if not t:
        return True
    if len(t) < 20:
        return True

    lower = t.lower()
    if "show_images" in lower or "---meta" in lower:
        return True
    if re.search(r"suggestions\s*\(", lower):
        return True
    if re.match(r"^:\s*true\b", t, re.I):
        return True

    if t.count("(") > t.count(")"):
        return True
    if t.count("[") > t.count("]"):
        return True
    if t.count("{") > t.count("}"):
        return True

    # Ends mid-number / mid-unit (common cut: "১৬৫০ মিমি")
    if re.search(r"\d+\s*(mm|mim|মিমি|মি\.?ম\.?|hp|rpm)?$", t, re.I):
        return True

    # Ends with conjunction / incomplete Bangla connectors
    if re.search(
        r"(এবং|ও|বা|কিন্তু|যদি|যে|দিয়ে|দিয়ে|করতে|হলো|হল|কাছে|থেকে|জন্য)\s*$",
        t,
    ):
        return True

    last = t[-1]
    if last not in _END_OK and last not in "০১২৩৪৫৬৭৮৯0123456789":
        # Mid-word Latin or dangling Bangla letter without sentence end
        if re.search(r"[A-Za-z]$", t) or re.search(r"[\u0980-\u09FF]$", t):
            return True

    # Promised a dealer list but phones never appeared
    if ("ডিলারদের কাছে" in t or "নিচের অনুমোদিত" in t) and "০১৭১৮২৩২৪০৬" not in t:
        return True

    return False


def looks_garbage(text: str) -> bool:
    t = strip_leaked_metadata(text or "").strip()
    if not t:
        return True
    lower = t.lower()
    if "show_images" in lower and len(t) < 200:
        return True
    if "suggestions" in lower and "bangla" in lower:
        return True
    bangla = len(re.findall(r"[\u0980-\u09FF]", t))
    if bangla < 8 and len(t) < 80:
        return True
    return False


def needs_polish(text: str) -> bool:
    return looks_incomplete(text) or looks_garbage(text)


def polish_prompt(user_text: str, draft: str) -> str:
    """Ask the model to analyze Q + draft and emit a complete concise answer + META."""
    draft_clean = strip_leaked_metadata(draft).strip() or "(empty or broken draft)"
    user = (user_text or "").strip()
    return (
        "You are a quality editor for BRRI Winnower 2024 farmer support replies.\n\n"
        "TASK: Read the farmer QUESTION and the DRAFT answer. Rewrite ONE final reply.\n\n"
        "HARD RULES:\n"
        "1. Visible answer MUST be COMPLETE — never cut mid-word, mid-sentence, or mid-list.\n"
        "2. Concise spoken Bangla. Not verbose. No markdown. No English meta notes.\n"
        "3. Keep correct BRRI Win2024 facts from the draft/knowledge (B65, air control, etc.).\n"
        "4. Do NOT invent shops, prices, or phone numbers not already in the draft/system knowledge.\n"
        "5. Diagnostic format when useful:\n"
        "   সমস্যা: …\n"
        "   সমাধান: (max 2 short steps)\n"
        "   সাবধান: (optional one line)\n"
        "6. After the FULL visible answer, append EXACTLY:\n"
        "---META---\n"
        '{"suggestions":["q1","q2","q3"],"show_images":true_or_false}\n'
        "7. Never put show_images / suggestions / ---META--- inside the visible Bangla text.\n"
        "8. If the draft is already complete and good, keep it (light cleanup only) then add META.\n\n"
        f"QUESTION:\n{user}\n\n"
        f"DRAFT:\n{draft_clean}\n\n"
        "FINAL REPLY (complete Bangla first, then ---META---):"
    )
