"""
Configuration module – all settings from environment variables.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Application ──────────────────────────────────────────────────────────
    APP_ENV: Literal["development", "production"] = "development"
    SECRET_KEY: str = "changeme-in-production"
    ALLOWED_ORIGINS: str = "*"

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/itmaturity"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/itmaturity"

    # ── Redis / Celery ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # ── Search providers ──────────────────────────────────────────────────────
    # Supported values: "stub", "serpapi", "tavily", "bing"
    SEARCH_PROVIDER: str = "stub"
    SERPAPI_KEY: str = ""
    TAVILY_API_KEY: str = ""
    BING_API_KEY: str = ""

    # ── LLM ───────────────────────────────────────────────────────────────────
    # Compatible with any OpenAI-compatible endpoint (OpenAI, Azure, vLLM …)
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.0
    LLM_MAX_TOKENS: int = 2048
    # Set to "demo" to run full pipeline with mocked LLM responses
    LLM_MODE: Literal["live", "demo"] = "demo"

    # ── Rate limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_PER_IP: int = 5           # requests per window
    RATE_LIMIT_WINDOW_SECONDS: int = 3600

    # ── Caching ───────────────────────────────────────────────────────────────
    CACHE_TTL_DAYS: int = 7

    # ── Evidence collection ───────────────────────────────────────────────────
    MAX_URLS_PER_RUN: int = 60
    FETCH_TIMEOUT_SECONDS: int = 20
    MAX_TEXT_CHARS_PER_DOC: int = 30_000
    EVIDENCE_WINDOW_START: int = 2023
    EVIDENCE_WINDOW_END: int = 2025

    # ── Filesystem ────────────────────────────────────────────────────────────
    ARTIFACTS_DIR: Path = Path("/artifacts")

    # ── Playwright ────────────────────────────────────────────────────────────
    USE_PLAYWRIGHT: bool = True
    PLAYWRIGHT_HEADLESS: bool = True


settings = Settings()
