"""Knowledge base loader.

Reads the local ``knowledge_base/`` directory:

* ``prompts.txt`` – the base system instruction.
* ``machine_data.json`` – the machine technical specification.
* ``reference_images.json`` – numbered catalogue of the intact-part reference
  images and their descriptions/troubleshooting context.
* ``collected/`` – field-collected faults, photos (with Drive links), dealers.

The cache reloads automatically when any of those files change on disk, so
edits during development take effect on the next request without restarting
uvicorn.
"""

import json
import logging
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

FIELD_PHOTO_BASE = 100
CAD_BASE = 200
SUBASM_BASE = 300

# Manual cache (mtime-checked on each ``get_knowledge_base()`` call).
_kb_cache: "KnowledgeBase | None" = None
_kb_mtimes: tuple[float, ...] | None = None


class KnowledgeBase:
    """In-memory view of the local knowledge base files."""

    def __init__(
        self,
        base_prompt: str,
        machine_data: dict[str, Any],
        reference_images: list[dict[str, Any]],
        fault_trees: list[dict[str, Any]] | None = None,
        field_photos: list[dict[str, Any]] | None = None,
        cad_drawings: list[dict[str, Any]] | None = None,
        subassembly_drawings: list[dict[str, Any]] | None = None,
        collected_dealers: list[dict[str, Any]] | None = None,
    ):
        self.base_prompt = base_prompt
        self.machine_data = machine_data
        self.fault_trees = fault_trees or []
        self.field_photos = field_photos or []
        self.cad_drawings = cad_drawings or []
        self.subassembly_drawings = subassembly_drawings or []
        self.collected_dealers = collected_dealers or []
        self.reference_images = reference_images
        self._by_name = {
            entry.get("image_name"): entry for entry in reference_images
        }
        self._by_number = {
            entry.get("image_number"): entry
            for entry in reference_images
            if entry.get("image_number") is not None
        }

    def get_image_description(self, image_name: str) -> str | None:
        """Return the description for a reference image by its filename."""
        entry = self._by_name.get(image_name)
        return entry.get("description") if entry else None

    def get_entry_by_number(self, number: int) -> dict[str, Any] | None:
        return self._by_number.get(number)

    def _reference_catalog_text(self) -> str:
        if not self.reference_images:
            return ""
        lines = []
        for entry in self.reference_images:
            lines.append(
                f"#{entry.get('image_number')} [{entry.get('image_name')}]: "
                f"{entry.get('description')}"
            )
        return "\n".join(lines)

    def _fault_trees_text(self) -> str:
        if not self.fault_trees:
            return ""
        lines = []
        for ft in self.fault_trees:
            symptom = ft.get("symptom_local_bn") or ft.get("symptom_paper") or ""
            part = ft.get("part_paper") or ""
            solution = (ft.get("solution_bn") or "").replace("\n", " ")
            photo_nums = ", ".join(ft.get("photo_numbers") or [])
            line = f"- {symptom} ({part}): {solution}"
            if photo_nums:
                line += f" [field photo #{photo_nums}]"
            lines.append(line)
        return "\n".join(lines)

    def _field_photos_text(self) -> str:
        if not self.field_photos:
            return ""
        lines = []
        for fp in self.field_photos:
            local = "yes" if fp.get("local_image") else "pending upload"
            related = ", ".join(fp.get("related_symptoms_bn") or [])
            line = (
                f"- Photo #{fp.get('photo_no')} {fp.get('part_paper')}: "
                f"local preview={local}"
            )
            if related:
                line += f"; symptoms={related}"
            lines.append(line)
        return "\n".join(lines)

    def _cad_drawings_text(self) -> str:
        if not self.cad_drawings:
            return ""
        by_sub: dict[str, list[str]] = {}
        for cad in self.cad_drawings:
            sub = cad.get("subsystem") or "other"
            part = cad.get("part_name") or ""
            num = cad.get("image_number")
            line = f"#{num} {part}"
            by_sub.setdefault(sub, []).append(line)
        lines = [
            "CAD CUTTING DRAWINGS (fabrication / replacement parts):",
            "When a mechanic or farmer needs dimensions, welding patterns, or to make a "
            "replacement plate, prefer these over field photos.",
        ]
        for sub, parts in sorted(by_sub.items()):
            lines.append(f"  [{sub}] " + "; ".join(parts[:8]))
            if len(parts) > 8:
                lines.append(f"    … +{len(parts) - 8} more in this group")
        return "\n".join(lines)

    def _subassembly_text(self) -> str:
        if not self.subassembly_drawings:
            return ""
        seen_titles: set[str] = set()
        lines = [
            "SUB-ASSEMBLY DIAGRAMS (exploded views — how parts fit together):",
        ]
        for sa in self.subassembly_drawings:
            title = sa.get("title") or ""
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            num = sa.get("image_number")
            desc = (sa.get("catalog_description") or "")[:120]
            lines.append(f"- #{num} {title}: {desc}")
        return "\n".join(lines)

    def build_system_instruction(self) -> str:
        machine_json = json.dumps(self.machine_data, ensure_ascii=False, indent=2)
        parts = [
            self.base_prompt.strip(),
            "",
            "=== MACHINE TECHNICAL SPECIFICATIONS (JSON) ===",
            machine_json,
            "=== END SPECIFICATIONS ===",
        ]
        catalog = self._reference_catalog_text()
        if catalog:
            parts += [
                "",
                "=== REFERENCE IMAGE CATALOGUE (intact parts) ===",
                "The following are known-good reference images of the machine's "
                "parts. Use them to recognise parts and compare against the user's "
                "photo. Some of these images may also be attached to this request.",
                catalog,
                "=== END REFERENCE IMAGE CATALOGUE ===",
            ]
        faults = self._fault_trees_text()
        if faults:
            parts += [
                "",
                "=== FIELD-COLLECTED FAULTS & SOLUTIONS (Patuakhali, Bangla) ===",
                "Prefer these local symptom names and step-by-step fixes when they match "
                "the farmer's question. Do not invent dealers or parts not listed elsewhere.",
                faults,
                "=== END FIELD-COLLECTED FAULTS ===",
            ]
        photos = self._field_photos_text()
        if photos:
            parts += [
                "",
                "=== FIELD PHOTO SLOTS (01–20) ===",
                "Local preview photos may be attached in the chat gallery. "
                "NEVER paste Google Drive folder links in farmer-facing replies. "
                "If the farmer asks for a photo, say the matching part will appear "
                "below this message (or ask them to tap for photos).",
                photos,
                "=== END FIELD PHOTO SLOTS ===",
            ]
        cad = self._cad_drawings_text()
        if cad:
            parts += ["", f"=== {cad.split(chr(10))[0]} ===", *cad.split("\n")[1:], "=== END CAD DRAWINGS ==="]
        subasm = self._subassembly_text()
        if subasm:
            parts += ["", "=== SUB-ASSEMBLY DIAGRAMS ===", subasm, "=== END SUB-ASSEMBLY DIAGRAMS ==="]
        return "\n".join(parts) + "\n"


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse %s: %s", path.name, exc)
        return []


def _field_photos_as_reference(field_photos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Turn imported field photos with local files into catalogue entries (#101–120)."""
    entries: list[dict[str, Any]] = []
    for fp in field_photos:
        local = fp.get("local_image")
        if not local:
            continue
        part = fp.get("part_paper") or ""
        related = fp.get("related_symptoms_bn") or []
        desc = (
            f"Field-collected photo #{fp.get('photo_no')} of {part} on a BRRI Win2024 "
            "winnower (Patuakhali field team). "
        )
        if related:
            desc += (
                f"Troubleshooting context: relates to local symptoms "
                f"({', '.join(related)}). "
            )
        desc += (
            "Show this in the in-app gallery so the farmer can see the part "
            "on a real machine. Never paste Google Drive links in the reply."
        )
        entries.append(
            {
                "image_number": fp.get("image_number"),
                "image_name": local,
                "description": desc.strip(),
                "source": "field_collection",
                "photo_no": fp.get("photo_no"),
                "drive_folder_url": fp.get("drive_folder_url"),
                "related_symptoms_bn": related,
            }
        )
    return entries


def _drawings_as_reference(drawings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Turn CAD / sub-assembly JSON rows into searchable catalogue entries."""
    entries: list[dict[str, Any]] = []
    for d in drawings:
        name = d.get("image_name")
        num = d.get("image_number")
        if not name or num is None:
            continue
        desc = d.get("catalog_description") or d.get("description") or ""
        part_label = d.get("part_name") or d.get("title") or name
        entries.append(
            {
                "image_number": num,
                "image_name": name,
                "description": desc,
                "source": d.get("source"),
                "subsystem": d.get("subsystem"),
                "keywords": d.get("keywords") or [],
                "part_name": d.get("part_name"),
                "title": d.get("title"),
                "field_photo_no": d.get("field_photo_no"),
            }
        )
    return entries


def _merge_reference_catalog(base: list[dict[str, Any]], extra: list[dict[str, Any]]) -> list[dict]:
    by_number = {e.get("image_number"): e for e in base}
    for entry in extra:
        by_number[entry["image_number"]] = entry
    merged = list(by_number.values())
    merged.sort(key=lambda e: e.get("image_number") or 999)
    return merged


def _kb_source_paths() -> tuple[Path, ...]:
    collected = settings.collected_dir
    paths = [
        settings.prompts_file,
        settings.machine_data_file,
        settings.reference_images_json,
        collected / "manifest.json",
        collected / "fault_trees.json",
        collected / "field_photos.json",
        collected / "cad_drawings.json",
        collected / "subassembly_drawings.json",
    ]
    return tuple(paths)


def _kb_source_mtimes() -> tuple[float, ...]:
    return tuple(p.stat().st_mtime if p.exists() else 0.0 for p in _kb_source_paths())


def _load_base_prompt() -> str:
    path = settings.prompts_file
    if not path.exists():
        logger.warning("prompts.txt not found at %s; using empty prompt.", path)
        return ""
    return path.read_text(encoding="utf-8")


def _load_machine_data() -> dict[str, Any]:
    path = settings.machine_data_file
    if not path.exists():
        logger.warning("machine_data.json not found at %s; using empty data.", path)
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse machine_data.json: %s", exc)
        return {}


def _load_reference_images() -> list[dict[str, Any]]:
    path = settings.reference_images_json
    base: list[dict[str, Any]] = []
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            base = data if isinstance(data, list) else []
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse reference_images.json: %s", exc)

    collected_dir = settings.collected_dir
    field_photos = _load_json_list(collected_dir / "field_photos.json")
    cad_drawings = _load_json_list(collected_dir / "cad_drawings.json")
    subassembly = _load_json_list(collected_dir / "subassembly_drawings.json")
    extras = (
        _field_photos_as_reference(field_photos)
        + _drawings_as_reference(cad_drawings)
        + _drawings_as_reference(subassembly)
    )
    if extras:
        return _merge_reference_catalog(base, extras)
    return base


def _build_kb() -> KnowledgeBase:
    collected_dir = settings.collected_dir
    kb = KnowledgeBase(
        base_prompt=_load_base_prompt(),
        machine_data=_load_machine_data(),
        reference_images=_load_reference_images(),
        fault_trees=_load_json_list(collected_dir / "fault_trees.json"),
        field_photos=_load_json_list(collected_dir / "field_photos.json"),
        cad_drawings=_load_json_list(collected_dir / "cad_drawings.json"),
        subassembly_drawings=_load_json_list(collected_dir / "subassembly_drawings.json"),
        collected_dealers=_load_json_list(collected_dir / "dealers.json"),
    )
    logger.info(
        "Knowledge base loaded (prompt chars=%d, machine keys=%d, reference images=%d, "
        "fault trees=%d, field photos=%d, cad=%d, sub-assembly=%d).",
        len(kb.base_prompt),
        len(kb.machine_data),
        len(kb.reference_images),
        len(kb.fault_trees),
        len(kb.field_photos),
        len(kb.cad_drawings),
        len(kb.subassembly_drawings),
    )
    return kb


def get_knowledge_base() -> KnowledgeBase:
    """Return the knowledge base, reloading if any source file changed on disk."""
    global _kb_cache, _kb_mtimes

    current = _kb_source_mtimes()
    if _kb_cache is None or current != _kb_mtimes:
        if _kb_cache is not None:
            logger.info("Knowledge base source file(s) changed — reloading.")
        _kb_cache = _build_kb()
        _kb_mtimes = current
    return _kb_cache


def reload_knowledge_base() -> KnowledgeBase:
    """Force an immediate reload (e.g. from the admin API endpoint)."""
    global _kb_cache, _kb_mtimes
    _kb_cache = None
    _kb_mtimes = None
    return get_knowledge_base()
