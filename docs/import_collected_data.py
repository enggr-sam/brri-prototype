#!/usr/bin/env python3
"""Import filled BRRI Win2024 data collection form into app-ready knowledge base files.

Extracts:
  - Problems & solutions (+ embedded fault photos from the ছবি নং column)
  - Photo catalog metadata (merges full Google Drive folder URLs from CSV)
  - Dealers, specs meta, sub-assembly drawings, CAD cutting drawings

Writes to ``backend/knowledge_base/collected/``:
  - fault_trees.json
  - field_photos.json
  - dealers.json
  - cad_drawings.json      (part cutting drawings + rich search metadata)
  - subassembly_drawings.json
  - manifest.json
  - photos/          (field + fault images keyed by photo slot)
  - cad/             (CAD cutting drawing images)
  - subassembly/     (sub-assembly exploded diagrams)

Usage:
  backend/.venv/bin/python docs/import_collected_data.py \\
      "BRRI_Win2024 data collection (09.08.26).docx" \\
      --csv photo_folder_links.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent
if str(DOCS_DIR) not in sys.path:
    sys.path.insert(0, str(DOCS_DIR))

from drawing_catalog import (  # noqa: E402
    lookup_cad_part,
    lookup_subassembly,
    subsystem_keywords,
)

try:
    from docx import Document
    from docx.oxml.ns import qn
except ImportError:
    print("Install python-docx: backend/.venv/bin/pip install python-docx", file=sys.stderr)
    raise

REPO_ROOT = Path(__file__).resolve().parent.parent
COLLECTED_DIR = REPO_ROOT / "backend" / "knowledge_base" / "collected"
FIELD_PHOTO_BASE = 100  # image_number = 100 + int(photo_no)
CAD_BASE = 200  # image_number = 200 + cad index
SUBASM_BASE = 300  # image_number = 300 + sub-assembly index

_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/tiff": ".tif",
}


def _cell_text(cell) -> str:
    return (cell.text or "").strip()


def _norm_header(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _headers(table) -> list[str]:
    if not table.rows:
        return []
    return [_cell_text(c) for c in table.rows[0].cells]


def _row_dict(table, row_index: int) -> dict[str, str]:
    headers = _headers(table)
    if row_index >= len(table.rows):
        return {}
    cells = table.rows[row_index].cells
    values = [_cell_text(c) for c in cells]
    if len(values) < len(headers):
        values.extend([""] * (len(headers) - len(values)))
    return dict(zip(headers, values))


def _table_records(table) -> list[dict[str, str]]:
    if len(table.rows) < 2:
        return []
    headers = _headers(table)
    records: list[dict[str, str]] = []
    for ri in range(1, len(table.rows)):
        rec = _row_dict(table, ri)
        if any(v for k, v in rec.items() if k != headers[0]):
            records.append(rec)
    return records


def _classify_table(headers: list[str]) -> str | None:
    h = [_norm_header(x) for x in headers]
    joined = " | ".join(h)
    if h[:3] == ["field key", "ক্ষেত্র", "মান"] and any("meta" in x for x in h):
        return "meta"
    if h[:3] == ["field key", "ক্ষেত্র", "মান"]:
        return "specs"
    if "sub-assembly" in joined:
        return "subassembly"
    if "সমাধান" in joined and ("ছবি নং" in joined or "field key" in joined):
        return "problems"
    if "cutting drawing" in joined or "parts name" in joined:
        return "cad"
    if "দোকান" in joined and "মোবাইল" in joined:
        return "dealers"
    if "google drive" in joined and "ছবি নং" in joined:
        return "photos"
    return None


def _extract_cell_images(cell, doc_part) -> list[bytes]:
    blobs: list[bytes] = []
    for blip in cell._element.findall(
        ".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip"
    ):
        r_id = blip.get(qn("r:embed"))
        if not r_id or r_id not in doc_part.related_parts:
            continue
        part = doc_part.related_parts[r_id]
        blobs.append(part.blob)
    return blobs


def _save_image(blob: bytes, dest: Path, content_type: str | None = None) -> Path:
    ext = _EXT.get(content_type or "", ".jpg")
    if dest.suffix.lower() not in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif"}:
        dest = dest.with_suffix(ext)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(blob)
    return dest


def _slug(text: str, fallback: str = "item") -> str:
    slug = re.sub(r"[^\w\u0980-\u09FF]+", "_", (text or "").strip().lower())
    slug = slug.strip("_")
    return slug[:60] or fallback


def _parse_photo_numbers(raw: str) -> list[str]:
    nums: list[str] = []
    for part in re.split(r"[,/|\s]+", raw or ""):
        part = part.strip()
        if re.fullmatch(r"\d{1,2}", part):
            nums.append(part.zfill(2))
    return nums


def _load_csv_links(csv_path: Path) -> dict[str, dict[str, str]]:
    by_no: dict[str, dict[str, str]] = {}
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            no = (row.get("photo_no") or "").strip()
            if no and no != "root":
                by_no[no.zfill(2)] = row
            elif no == "root":
                by_no["root"] = row
    return by_no


def _pick_key(row: dict[str, str], *candidates: str) -> str:
    norm_map = {_norm_header(k): k for k in row}
    for cand in candidates:
        key = norm_map.get(_norm_header(cand))
        if key and row.get(key):
            return row[key]
    return ""


def _find_csv(csv_arg: Path | None) -> Path | None:
    if csv_arg and csv_arg.is_file():
        return csv_arg
    for candidate in (
        REPO_ROOT / "photo_folder_links.csv",
        REPO_ROOT / "docs" / "photo_folder_links.csv",
    ):
        if candidate.is_file():
            return candidate
    return None


def import_docx(doc_path: Path, csv_path: Path | None, out_dir: Path) -> dict:
    doc = Document(str(doc_path))
    csv_links = _load_csv_links(csv_path) if csv_path else {}

    photos_dir = out_dir / "photos"
    subasm_dir = out_dir / "subassembly"
    cad_dir = out_dir / "cad"
    for d in (photos_dir, subasm_dir, cad_dir):
        d.mkdir(parents=True, exist_ok=True)

    tables_by_kind: dict[str, list] = {}
    for table in doc.tables:
        kind = _classify_table(_headers(table))
        if kind:
            tables_by_kind.setdefault(kind, []).append(table)

    # --- Specs & meta ---
    # Field keys repeat (Motor = HP, kW and RPM), so keep rows as a list and use the
    # Bangla label to disambiguate instead of collapsing into a dict.
    specs: list[dict[str, str]] = []
    meta: dict[str, str] = {}
    for table in tables_by_kind.get("specs", []) + tables_by_kind.get("meta", []):
        for row in table.rows[1:]:
            key = _cell_text(row.cells[0])
            label = _cell_text(row.cells[1]) if len(row.cells) > 1 else ""
            val = _cell_text(row.cells[2]) if len(row.cells) > 2 else ""
            if not key:
                continue
            if key.lower().startswith("meta"):
                meta[key] = val
            else:
                specs.append({"field_key": key, "label_bn": label, "value": val})

    root_link = ""
    if "root" in csv_links:
        root_link = csv_links["root"].get("folder_link", "")
    elif meta.get("Meta drive root link"):
        root_link = meta["Meta drive root link"]

    # --- Problems + fault images ---
    fault_trees: list[dict] = []
    fault_images_by_slot: dict[str, str] = {}
    seen_fault_ids: dict[str, int] = {}
    for table in tables_by_kind.get("problems", []):
        for ri in range(1, len(table.rows)):
            row = table.rows[ri]
            rec = _row_dict(table, ri)
            field_key = _pick_key(rec, "Field key", "field_key")
            if not field_key:
                continue

            # The form can repeat a field key on two rows; keep both distinguishable
            # so neither the record nor its image is overwritten by the other.
            base_id = field_key.replace(" ", ".").lower()
            seen_fault_ids[base_id] = seen_fault_ids.get(base_id, 0) + 1
            occurrence = seen_fault_ids[base_id]
            fault_id = base_id if occurrence == 1 else f"{base_id}.{occurrence}"

            photo_raw = _pick_key(rec, "ছবি নং", "photo_no")
            photo_numbers = _parse_photo_numbers(photo_raw)

            fault_image = ""
            blobs = _extract_cell_images(row.cells[-1], doc.part)
            if not blobs and len(row.cells) > 6:
                blobs = _extract_cell_images(row.cells[6], doc.part)
            if blobs:
                slug = _slug(fault_id, f"fault_{ri}")
                fname = f"fault_{slug}.jpg"
                _save_image(blobs[0], photos_dir / fname)
                fault_image = fname
                for pno in photo_numbers or ["00"]:
                    if pno != "00":
                        slot_fname = f"field_{pno}.jpg"
                        _save_image(blobs[0], photos_dir / slot_fname)
                        fault_images_by_slot[pno] = slot_fname

            symptom_local = _pick_key(rec, "স্থানীয় ভাষায় সমস্যার নাম", "স্থানীয় ভাষায় সমস্যার নাম")
            part_local = _pick_key(rec, "স্থানীয় নাম", "স্থানীয় নাম")
            keywords = sorted(
                {
                    t
                    for t in re.split(r"[^\w\u0980-\u09FF]+", f"{symptom_local} {part_local}".lower())
                    if len(t) >= 2
                }
            )

            fault_trees.append(
                {
                    "id": fault_id,
                    "field_key": field_key,
                    "part_paper": _pick_key(rec, "অংশ (পেপার)", "part_paper"),
                    "part_local_bn": part_local,
                    "symptom_paper": _pick_key(rec, "সমস্যা (পেপার)", "symptom_paper"),
                    "symptom_local_bn": symptom_local,
                    "solution_bn": _pick_key(rec, "সমাধান", "solution_bn"),
                    "photo_numbers": photo_numbers,
                    "fault_image": fault_image,
                    "keywords": keywords,
                }
            )

    # --- Photo catalog (merge CSV links) ---
    field_photos: list[dict] = []
    for table in tables_by_kind.get("photos", []):
        for ri in range(1, len(table.rows)):
            rec = _row_dict(table, ri)
            photo_no = _pick_key(rec, "ছবি নং", "photo_no").zfill(2)
            if not photo_no or photo_no == "00":
                continue

            csv_row = csv_links.get(photo_no, {})
            drive_url = csv_row.get("folder_link") or _pick_key(rec, "Google Drive লিংক", "drive_link")
            related = _pick_key(rec, "সম্পর্কিত সমস্যা (স্থানীয়)", "related_symptoms")
            related_list = [s.strip() for s in re.split(r"[,;]", related) if s.strip()]

            local_image = fault_images_by_slot.get(photo_no, "")
            image_number = FIELD_PHOTO_BASE + int(photo_no)

            field_photos.append(
                {
                    "photo_no": photo_no,
                    "field_key": _pick_key(rec, "Field key", "field_key"),
                    "part_paper": _pick_key(rec, "অংশ (পেপার)", "part_paper"),
                    "part_local_bn": _pick_key(rec, "স্থানীয় নাম", "part_local_bn"),
                    "folder_name": csv_row.get("folder_name")
                    or _pick_key(rec, "ফোল্ডার নাম", "folder_name"),
                    "filename": csv_row.get("filename")
                    or _pick_key(rec, "ফাইল নাম (মূল ছবি)", "filename"),
                    "drive_folder_url": drive_url,
                    "related_symptoms_bn": related_list,
                    "local_image": local_image,
                    "image_number": image_number,
                    "source": "field_collection",
                }
            )

    field_photos.sort(key=lambda x: x["photo_no"])

    # --- Dealers ---
    dealers: list[dict] = []
    for table in tables_by_kind.get("dealers", []):
        for rec in _table_records(table):
            name = _pick_key(rec, "দোকান (বাংলা)", "name_bn")
            if not name:
                continue
            mobile = _pick_key(rec, "মোবাইল", "mobile")
            dealers.append(
                {
                    "field_key": _pick_key(rec, "Field key", "field_key"),
                    "name_bn": name,
                    "address_bn": _pick_key(rec, "ঠিকানা", "address_bn"),
                    "mobile": mobile,
                    "mobile_bn": mobile,
                    "parts": _pick_key(rec, "যন্ত্রাংশ", "parts"),
                    "note_bn": _pick_key(rec, "নোট", "note_bn"),
                }
            )

    # --- Sub-assembly embedded diagrams (with rich metadata) ---
    subassembly: list[dict] = []
    for table in tables_by_kind.get("subassembly", []):
        current_title = ""
        for ri in range(1, len(table.rows)):
            rec = _row_dict(table, ri)
            title = _pick_key(rec, "Sub-Assembly", "sub-assembly")
            if title:
                current_title = title
            part_desc = _pick_key(rec, "বিবরণ", "description")
            sheet = _pick_key(rec, "DRG / Sheet", "sheet")
            row = table.rows[ri]
            blobs: list[bytes] = []
            for cell in row.cells[1:]:
                blobs = _extract_cell_images(cell, doc.part)
                if blobs:
                    break
            if not (blobs or current_title or part_desc):
                continue

            entry_meta = lookup_subassembly(current_title)
            fname = ""
            if blobs:
                slug = _slug(current_title or part_desc or f"subasm_{ri}")
                fname = f"subasm_{ri:02d}_{slug}.jpg"
                _save_image(blobs[0], subasm_dir / fname)

            idx = len(subassembly) + 1
            subsystem = entry_meta.get("subsystem", "")
            keywords = list(dict.fromkeys(
                (entry_meta.get("keywords") or [])
                + list(subsystem_keywords(subsystem))
                + _tokenize_keywords(current_title)
            ))
            desc = entry_meta.get("description") or (
                f"Sub-assembly diagram: {current_title}. {part_desc}".strip()
            )
            subassembly.append(
                {
                    "index": idx,
                    "title": current_title,
                    "sheet": sheet,
                    "description": part_desc,
                    "image_name": fname,
                    "image_number": SUBASM_BASE + idx,
                    "subsystem": subsystem,
                    "keywords": keywords,
                    "catalog_description": desc,
                    "field_photo_no": entry_meta.get("field_photo_no"),
                    "source": "subassembly_drawing",
                }
            )

    # --- CAD cutting drawings (with rich metadata) ---
    cad_drawings: list[dict] = []
    for table in tables_by_kind.get("cad", []):
        for ri in range(1, len(table.rows)):
            rec = _row_dict(table, ri)
            part_name = _pick_key(rec, "Parts name", "part_name")
            row = table.rows[ri]
            blobs: list[bytes] = []
            for cell in row.cells:
                blobs = _extract_cell_images(cell, doc.part)
                if blobs:
                    break
            if not (blobs or part_name):
                continue

            entry_meta = lookup_cad_part(part_name)
            fname = ""
            if blobs:
                slug = _slug(part_name or f"cad_{ri}")
                fname = f"cad_{ri:02d}_{slug}.jpg"
                _save_image(blobs[0], cad_dir / fname)

            idx = len(cad_drawings) + 1
            subsystem = entry_meta.get("subsystem", "")
            keywords = list(dict.fromkeys(
                (entry_meta.get("keywords") or [])
                + list(subsystem_keywords(subsystem))
                + _tokenize_keywords(part_name)
            ))
            desc = entry_meta.get("description") or (
                f"CAD cutting drawing for {part_name} (BRRI Win2024 winnower)."
            )
            cad_drawings.append(
                {
                    "index": idx,
                    "part_name": part_name,
                    "image_name": fname,
                    "image_number": CAD_BASE + idx,
                    "subsystem": subsystem,
                    "keywords": keywords,
                    "catalog_description": desc,
                    "field_photo_no": entry_meta.get("field_photo_no"),
                    "source": "cad_drawing",
                }
            )

    manifest = {
        "source_file": doc_path.name,
        "csv_file": csv_path.name if csv_path else None,
        "drive_root_url": root_link,
        "collector_meta": meta,
        "counts": {
            "specs": len(specs),
            "fault_trees": len(fault_trees),
            "field_photos": len(field_photos),
            "field_photos_with_local_image": sum(1 for p in field_photos if p["local_image"]),
            "dealers": len(dealers),
            "cad_drawings": len(cad_drawings),
            "cad_drawings_without_image": sum(1 for c in cad_drawings if not c["image_name"]),
            "subassembly_drawings": len(subassembly),
            "subassembly_without_image": sum(1 for s in subassembly if not s["image_name"]),
        },
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "specs.json").write_text(
        json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "fault_trees.json").write_text(
        json.dumps(fault_trees, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "field_photos.json").write_text(
        json.dumps(field_photos, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "dealers.json").write_text(
        json.dumps(dealers, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "subassembly_drawings.json").write_text(
        json.dumps(subassembly, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "cad_drawings.json").write_text(
        json.dumps(cad_drawings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return manifest


def _tokenize_keywords(text: str) -> list[str]:
    return [t for t in re.split(r"[^\w\u0980-\u09FF]+", (text or "").lower()) if len(t) >= 3]


def main() -> None:
    parser = argparse.ArgumentParser(description="Import filled BRRI form into knowledge base")
    parser.add_argument("docx", type=Path, help="Filled .docx from Google Docs export")
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="photo_folder_links.csv (default: repo root or docs/)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=COLLECTED_DIR,
        help=f"Output directory (default: {COLLECTED_DIR})",
    )
    args = parser.parse_args()

    if not args.docx.is_file():
        print(f"File not found: {args.docx}", file=sys.stderr)
        sys.exit(1)

    csv_path = _find_csv(args.csv)
    if not csv_path:
        print("Warning: photo_folder_links.csv not found — Drive links may stay truncated.", file=sys.stderr)

    manifest = import_docx(args.docx.resolve(), csv_path, args.out.resolve())
    print(f"Imported → {args.out.resolve()}")
    for key, val in manifest["counts"].items():
        print(f"  {key}: {val}")
    if manifest.get("drive_root_url"):
        print(f"  drive_root: {manifest['drive_root_url'][:60]}...")


if __name__ == "__main__":
    main()
