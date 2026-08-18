"""LLM shortlist picker — chooses the best reference images for this turn."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def build_image_reason_prompt(
    focus: str,
    user_text: str,
    candidates: list[dict],
    *,
    wants_photos: bool,
) -> str:
    lines = []
    for c in candidates:
        num = c.get("image_number")
        name = c.get("image_name") or ""
        label = c.get("part_name") or c.get("title") or name
        src = c.get("source") or "reference"
        desc = (c.get("description") or "")[:180]
        lines.append(f"#{num} [{src}] {label}: {desc}")

    want = "YES — farmer asked for photos / visual help" if wants_photos else (
        "ONLY if a photo clearly helps this specific fix; otherwise pick []"
    )
    return (
        "You select reference photos for a BRRI Winnower 2024 farmer chat.\n"
        "Think: what part/symptom is this conversation about? Then pick ONLY matching images.\n\n"
        f"Conversation focus:\n{focus.strip()}\n\n"
        f"Current user message:\n{(user_text or '').strip()}\n\n"
        f"Farmer wants photos now? {want}\n\n"
        "Candidates (choose from these ONLY):\n"
        + "\n".join(lines)
        + "\n\n"
        "Rules:\n"
        "- Pick 0–3 image numbers that best match the focus (air control ≠ sieve ≠ show cover).\n"
        "- Prefer real machine / field / air-control photos for air/বাতাস questions.\n"
        "- Never pick unrelated drawings just to fill slots.\n"
        "- If nothing fits, return [].\n"
        "- Reply with ONLY JSON: {\"images\":[13,14],\"reason\":\"short English\"}\n"
    )


def parse_image_reason_response(text: str, allowed: set[int]) -> list[int]:
    raw = (text or "").strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    nums = data.get("images") or data.get("image_numbers") or []
    out: list[int] = []
    seen: set[int] = set()
    for n in nums:
        try:
            num = int(n)
        except (TypeError, ValueError):
            continue
        if num in allowed and num not in seen:
            seen.add(num)
            out.append(num)
        if len(out) >= 3:
            break
    return out


def paths_for_numbers(
    numbers: list[int],
    entries_by_number: dict[int, dict],
    resolve_path,
    limit: int = 3,
) -> list[Path]:
    paths: list[Path] = []
    for num in numbers:
        if len(paths) >= limit:
            break
        entry = entries_by_number.get(num)
        if not entry:
            continue
        path = resolve_path(entry.get("image_name") or "")
        if path is not None:
            paths.append(path)
    return paths
