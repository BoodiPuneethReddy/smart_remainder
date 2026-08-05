"""
app/main.py — FastAPI application entry point.

Startup sequence:
  1. Create all DB tables
  2. Seed demo data (idempotent)
  3. Run initial priority scoring for seeded tasks
  4. Start APScheduler for reminder polling

All routes are mounted here under /api/*.
"""

import sys
import io
import logging
from contextlib import asynccontextmanager

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import create_all_tables, SessionLocal
import app.models  # noqa: F401 — registers all models with Base
from app.seed.seed_data import seed_database
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.ai_client import get_ai_client
from app.agents.planner_agent import score_all_tasks
from app.models.user import User

from app.api.routes import auth, tasks, planner, chat, reminders, analytics, assessment
from app.api.routes import colleges as colleges_router
from app.api.routes import import_routes
from app.services.document_import.ocr_status import OCR_AVAILABLE

settings = get_settings()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — startup and shutdown."""
    logger.info("=== Smart Study Reminder AI starting up ===")

    # 1. Database tables
    create_all_tables()
    logger.info("Database tables created/verified")

    # 2. Seed demo data
    db = SessionLocal()
    try:
        seed_database(db)

        # 3. Score all seeded tasks so priority scores are ready immediately
        ai_client = get_ai_client()
        client_name = type(ai_client).__name__
        key_loaded = bool(settings.gemini_api_key and "YOUR_GEMINI" not in settings.gemini_api_key.upper())
        fallback_disabled = settings.disable_ai_fallback

        logger.info(
            "\n============================================================\n"
            "AI CLIENT ASSERTION REPORT:\n"
            "AI CLIENT = %s\n"
            "Model = %s\n"
            "Fallback Disabled = %s\n"
            "API Key Loaded = %s\n"
            "============================================================",
            client_name, settings.gemini_model, fallback_disabled, key_loaded
        )
        users = db.query(User).all()
        for user in users:
            try:
                scored = score_all_tasks(user.id, db, ai_client)
                logger.info(
                    "Scored %d tasks for user '%s'", len(scored), user.email
                )
            except Exception as exc:
                logger.warning("Could not score tasks for user %d: %s", user.id, exc)

        # 4. Seed college directory (idempotent — runs only if table is empty)
        try:
            from app.seed.seed_colleges import seed_colleges
            seed_colleges(db)
        except Exception as exc:
            logger.warning("College seeder failed: %s", exc)
    finally:
        db.close()

    logger.info("Tesseract OCR: %s", 'available' if OCR_AVAILABLE else 'unavailable — image imports disabled')

    # 4. Start reminder scheduler
    start_scheduler()

    logger.info("=== Backend ready — http://localhost:8000/docs ===")
    yield

    # Shutdown
    stop_scheduler()
    logger.info("=== Smart Study Reminder AI shut down ===")


app = FastAPI(
    title="Smart Study Reminder AI",
    description="Agentic AI study coach — ByteXL × AMD Mini Hackathon",
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS — allow the React frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers
app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(planner.router)
app.include_router(chat.router)
app.include_router(reminders.router)
app.include_router(analytics.router)
app.include_router(colleges_router.router)
app.include_router(import_routes.router)
app.include_router(assessment.router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "ai_mode": settings.ai_service_mode,
    }
