"""Knowledge base loader.

Reads the local ``knowledge_base/`` directory: the base system prompt
(``prompts.txt``) and the machine specification (``machine_data.json``). The
content is cached in-process and can be force-reloaded, which is handy during
development when the files change.
"""

import json
import logging
from functools import lru_cache
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """In-memory view of the local knowledge base files."""

    def __init__(self, base_prompt: str, machine_data: dict[str, Any]):
        self.base_prompt = base_prompt
        self.machine_data = machine_data

    def build_system_instruction(self) -> str:
        """Combine the base prompt with the machine JSON into one instruction.

        This is the text fed to Gemini as the system instruction so every
        answer is grounded in the BRRI Winnower's real specifications.
        """
        machine_json = json.dumps(self.machine_data, ensure_ascii=False, indent=2)
        return (
            f"{self.base_prompt.strip()}\n\n"
            "=== MACHINE TECHNICAL SPECIFICATIONS (JSON) ===\n"
            f"{machine_json}\n"
            "=== END SPECIFICATIONS ===\n"
        )


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


@lru_cache
def get_knowledge_base() -> KnowledgeBase:
    """Return the cached knowledge base (loaded once per process)."""
    kb = KnowledgeBase(
        base_prompt=_load_base_prompt(),
        machine_data=_load_machine_data(),
    )
    logger.info(
        "Knowledge base loaded (prompt chars=%d, machine keys=%d).",
        len(kb.base_prompt),
        len(kb.machine_data),
    )
    return kb


def reload_knowledge_base() -> KnowledgeBase:
    """Clear the cache and reload the knowledge base from disk."""
    get_knowledge_base.cache_clear()
    return get_knowledge_base()
