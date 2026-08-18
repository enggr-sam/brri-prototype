"""Application configuration.

All settings are loaded from environment variables (see ``.env.example``).
Using ``pydantic-settings`` keeps configuration typed, validated, and centralised
so the rest of the codebase never has to touch ``os.environ`` directly.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute path to the ``backend/`` directory. Everything (knowledge base,
# uploads, SQLite file) is resolved relative to this so the app runs the same
# regardless of the current working directory.
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Strongly-typed application settings sourced from the environment."""

    # --- Secrets / external services -------------------------------------
    GEMINI_API_KEY: str = ""
    # Primary multimodal model. gemini-2.0-flash works on paid API keys.
    # gemini-2.5-pro may 404 for newer accounts — use gemini-2.5-flash instead.
    GEMINI_MODEL: str = "gemini-2.0-flash"
    # Tried automatically when the primary model returns 429/404/503.
    GEMINI_FALLBACK_MODEL: str = "gemini-flash-latest"
    # Cheap/fast model for the helper stages (image picking, gallery captions) that
    # produce short output and do not need the answer model. Empty = use the main chain.
    GEMINI_FAST_MODEL: str = "gemini-flash-lite-latest"

    @property
    def model_chain(self) -> list[str]:
        """Ordered, de-duplicated list of models to try (primary → fallback)."""
        chain = [self.GEMINI_MODEL]
        if self.GEMINI_FALLBACK_MODEL and self.GEMINI_FALLBACK_MODEL not in chain:
            chain.append(self.GEMINI_FALLBACK_MODEL)
        return chain

    @property
    def fast_model_chain(self) -> list[str]:
        """Models for helper stages, falling back to the main chain."""
        chain: list[str] = []
        if self.GEMINI_FAST_MODEL:
            chain.append(self.GEMINI_FAST_MODEL)
        for model in self.model_chain:
            if model not in chain:
                chain.append(model)
        return chain

    # --- Database ---------------------------------------------------------
    # SQLite by default. Swapping to PostgreSQL/MySQL later only requires
    # changing this URL (and installing the relevant driver).
    DATABASE_URL: str = f"sqlite:///{BACKEND_DIR / 'brri_winnower.db'}"

    @property
    def resolved_database_url(self) -> str:
        """Return the DB URL with relative SQLite paths anchored to BACKEND_DIR.

        A URL like ``sqlite:///./brri_winnower.db`` is relative to the process's
        working directory, which breaks (e.g. "attempt to write a readonly
        database") when uvicorn is launched from a non-writable directory. We
        rewrite such relative paths to an absolute location under ``backend/``
        so the database always lives in a known, writable place regardless of
        the launch directory. Non-SQLite URLs are returned unchanged.
        """
        prefix = "sqlite:///"
        if not self.DATABASE_URL.startswith(prefix):
            return self.DATABASE_URL

        path_part = self.DATABASE_URL[len(prefix):]
        # In-memory or already-absolute ("sqlite:////abs") paths are left alone.
        if path_part.startswith(":memory:") or path_part.startswith("/"):
            return self.DATABASE_URL

        abs_path = (BACKEND_DIR / path_part).resolve()
        return f"sqlite:///{abs_path}"

    # --- CORS -------------------------------------------------------------
    # Comma-separated list of origins allowed to call the API.
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Reference images (Gemini grounding) -----------------------------
    # How many intact-part photos to attach per request (descriptions for all
    # 36 parts are still injected as text in the system instruction).
    MAX_REFERENCE_IMAGES: int = 3
    # Minimum relevance score (see reference_selector) to attach an image.
    REFERENCE_IMAGE_MIN_SCORE: float = 4.0

    # --- Latency / cost controls ------------------------------------------
    # Each turn costs one model call per stage. These skip stages that are not
    # needed for the current turn.
    # Only run the polish/editor pass when the streamed draft looks incomplete.
    POLISH_ONLY_WHEN_NEEDED: bool = True
    # Generate per-image gallery captions (extra call; UI has a Bangla default).
    ENABLE_IMAGE_CAPTIONS: bool = True
    # Skip the LLM image picker when the top-ranked image already wins clearly.
    # Ratio of best score to runner-up above which the ranking is trusted as-is.
    IMAGE_REASONER_SKIP_MARGIN: float = 1.6

    # --- Filesystem locations --------------------------------------------
    KNOWLEDGE_BASE_DIR: Path = BACKEND_DIR / "knowledge_base"
    UPLOAD_DIR: Path = BACKEND_DIR / "uploads"

    model_config = SettingsConfigDict(
        # Absolute path so the .env is found no matter which directory uvicorn
        # is launched from (relative "env_file" is resolved against the CWD).
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a clean list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def prompts_file(self) -> Path:
        return self.KNOWLEDGE_BASE_DIR / "prompts.txt"

    @property
    def machine_data_file(self) -> Path:
        return self.KNOWLEDGE_BASE_DIR / "machine_data.json"

    @property
    def reference_images_json(self) -> Path:
        return self.KNOWLEDGE_BASE_DIR / "reference_images.json"

    @property
    def reference_images_dir(self) -> Path:
        return self.KNOWLEDGE_BASE_DIR / "reference_images"

    @property
    def collected_dir(self) -> Path:
        return self.KNOWLEDGE_BASE_DIR / "collected"

    @property
    def collected_photos_dir(self) -> Path:
        return self.collected_dir / "photos"

    @property
    def collected_cad_dir(self) -> Path:
        return self.collected_dir / "cad"

    @property
    def collected_subassembly_dir(self) -> Path:
        return self.collected_dir / "subassembly"


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance (parsed once per process)."""
    return Settings()


settings = get_settings()
