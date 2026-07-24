"""FastAPI application entrypoint for the BRRI Winnower 2024 support assistant.

Run locally with:

    uvicorn main:app --reload --port 8000

Interactive docs are then available at http://localhost:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routes.knowledge_base import router as knowledge_base_router
from app.routes.troubleshoot import router as troubleshoot_router
from app.services.knowledge_base import get_knowledge_base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("brri")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hooks: create tables, ensure dirs, warm the KB cache."""
    logger.info("Starting BRRI Winnower 2024 support API...")
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    settings.reference_images_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    kb = get_knowledge_base()
    logger.info("Loaded machine: %s", kb.machine_data.get("machine_name", "unknown"))
    yield
    logger.info("Shutting down BRRI Winnower 2024 support API.")


app = FastAPI(
    title="BRRI Winnower 2024 Support API",
    description=(
        "Multimodal troubleshooting assistant for the BRRI Winnower Model 2024. "
        "Accepts image and voice inputs and returns step-by-step guidance in Bengali."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(troubleshoot_router)
app.include_router(knowledge_base_router)


@app.get("/", tags=["health"])
def root() -> dict:
    """Simple liveness + configuration probe."""
    return {
        "status": "ok",
        "service": "BRRI Winnower 2024 Support API",
        "model": settings.GEMINI_MODEL,
        "gemini_configured": bool(settings.GEMINI_API_KEY),
    }


@app.get("/api/health", tags=["health"])
def health() -> dict:
    return {"status": "healthy"}
