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
    GEMINI_MODEL: str = "gemini-2.5-pro"

    # --- Database ---------------------------------------------------------
    # SQLite by default. Swapping to PostgreSQL/MySQL later only requires
    # changing this URL (and installing the relevant driver).
    DATABASE_URL: str = f"sqlite:///{BACKEND_DIR / 'brri_winnower.db'}"

    # --- CORS -------------------------------------------------------------
    # Comma-separated list of origins allowed to call the API.
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Filesystem locations --------------------------------------------
    KNOWLEDGE_BASE_DIR: Path = BACKEND_DIR / "knowledge_base"
    UPLOAD_DIR: Path = BACKEND_DIR / "uploads"

    model_config = SettingsConfigDict(
        env_file=".env",
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
    def reference_images_dir(self) -> Path:
        return self.KNOWLEDGE_BASE_DIR / "reference_images"


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance (parsed once per process)."""
    return Settings()


settings = get_settings()
