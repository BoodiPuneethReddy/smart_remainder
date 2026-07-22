"""
core/config.py — Application configuration loaded from environment variables.
Uses pydantic-settings so every setting is validated and typed at startup.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ────────────────────────────────────────────────────────────
    app_name: str = "Smart Study Reminder AI"
    app_version: str = "1.0.0"
    debug: bool = False

    # ── Auth ──────────────────────────────────────────────────────────────────
    secret_key: str = "dev-secret-key-change-in-production-32chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./study_reminder.db"

    # ── AI Service ────────────────────────────────────────────────────────────
    # "local" → template-based LocalAIService (zero external deps)
    # "remote" → RemoteAIService calling AMD JupyterLab endpoint
    ai_service_mode: str = "local"
    ai_service_url: str = "https://dub.aupcloud.io/aipc-14"
    ai_service_token: str = ""
    ai_service_timeout: float = 10.0  # seconds before falling back to local

    # ── Scheduler ─────────────────────────────────────────────────────────────
    reminder_poll_interval: int = 60  # seconds

    # ── CORS ──────────────────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:5173"

    # ── Dev Mode & SMTP Configuration ──────────────────────────────────────────
    dev_mode: bool = True
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_name: str = "Smart Study Reminder AI"
    smtp_from_email: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — import and call this everywhere."""
    return Settings()
