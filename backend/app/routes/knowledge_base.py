"""Knowledge base admin routes (reload catalogue without restart)."""

from fastapi import APIRouter

from app.services.knowledge_base import get_knowledge_base, reload_knowledge_base

router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge-base"])


@router.get("/status")
def knowledge_base_status() -> dict:
    """Return a snapshot of what is currently loaded in the KB cache."""
    kb = get_knowledge_base()
    return {
        "reference_image_count": len(kb.reference_images),
        "fault_tree_count": len(kb.fault_trees),
        "field_photo_count": len(kb.field_photos),
        "field_photos_with_local_image": sum(1 for p in kb.field_photos if p.get("local_image")),
        "cad_drawing_count": len(kb.cad_drawings),
        "subassembly_drawing_count": len(kb.subassembly_drawings),
        "machine_name": kb.machine_data.get("machine_name"),
        "prompt_chars": len(kb.base_prompt),
    }


@router.post("/reload")
def knowledge_base_reload() -> dict:
    """Force-reload prompts, machine_data.json, and reference_images.json."""
    kb = reload_knowledge_base()
    return {
        "status": "reloaded",
        "reference_image_count": len(kb.reference_images),
        "fault_tree_count": len(kb.fault_trees),
        "field_photo_count": len(kb.field_photos),
        "cad_drawing_count": len(kb.cad_drawings),
        "subassembly_drawing_count": len(kb.subassembly_drawings),
        "machine_name": kb.machine_data.get("machine_name"),
    }
