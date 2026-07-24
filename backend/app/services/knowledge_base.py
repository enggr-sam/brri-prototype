"""Knowledge base loader.

Reads the local ``knowledge_base/`` directory:

* ``prompts.txt`` – the base system instruction.
* ``machine_data.json`` – the machine technical specification.
* ``reference_images.json`` – numbered catalogue of the intact-part reference
  images and their descriptions/troubleshooting context.

The content is cached in-process and can be force-reloaded, which is handy
during development when the files change.
"""

import json
import logging
from functools import lru_cache
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """In-memory view of the local knowledge base files."""

    def __init__(
        self,
        base_prompt: str,
        machine_data: dict[str, Any],
        reference_images: list[dict[str, Any]],
    ):
        self.base_prompt = base_prompt
        self.machine_data = machine_data
        self.reference_images = reference_images
        # Fast lookup: final image filename -> catalogue entry.
        self._by_name = {
            entry.get("image_name"): entry for entry in reference_images
        }

    def get_image_description(self, image_name: str) -> str | None:
        """Return the description for a reference image by its filename."""
        entry = self._by_name.get(image_name)
        return entry.get("description") if entry else None

    def _reference_catalog_text(self) -> str:
        """A compact text catalogue of every reference image (number, name,
        description) so the model knows what intact parts exist even when only a
        few images are attached to a given request."""
        if not self.reference_images:
            return ""
        lines = []
        for entry in self.reference_images:
            lines.append(
                f"#{entry.get('image_number')} [{entry.get('image_name')}]: "
                f"{entry.get('description')}"
            )
        return "\n".join(lines)

    def build_system_instruction(self) -> str:
        """Combine the base prompt with the machine JSON and the reference-image
        catalogue into one grounded system instruction fed to Gemini.
        """
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
        return "\n".join(parts) + "\n"


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
    if not path.exists():
        logger.warning("reference_images.json not found at %s; using empty list.", path)
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse reference_images.json: %s", exc)
        return []


@lru_cache
def get_knowledge_base() -> KnowledgeBase:
    """Return the cached knowledge base (loaded once per process)."""
    kb = KnowledgeBase(
        base_prompt=_load_base_prompt(),
        machine_data=_load_machine_data(),
        reference_images=_load_reference_images(),
    )
    logger.info(
        "Knowledge base loaded (prompt chars=%d, machine keys=%d, reference images=%d).",
        len(kb.base_prompt),
        len(kb.machine_data),
        len(kb.reference_images),
    )
    return kb


def reload_knowledge_base() -> KnowledgeBase:
    """Clear the cache and reload the knowledge base from disk."""
    get_knowledge_base.cache_clear()
    return get_knowledge_base()
