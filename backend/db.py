"""
Database setup – async SQLAlchemy engine + sync engine for Alembic/Celery.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine, event

from backend.config import settings
from backend.models import Base

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# ── Async engine (used by FastAPI endpoints) ──────────────────────────────────
_async_kwargs = {"echo": False}
if not _is_sqlite:
    _async_kwargs["pool_pre_ping"] = True

async_engine = create_async_engine(settings.DATABASE_URL, **_async_kwargs)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── Sync engine (used by Celery workers / inline fallback) ────────────────────
_sync_kwargs = {"echo": False}
if not _is_sqlite:
    _sync_kwargs["pool_pre_ping"] = True

sync_engine = create_engine(settings.DATABASE_URL_SYNC, **_sync_kwargs)

# Enable WAL mode and foreign keys for SQLite
if _is_sqlite:
    @event.listens_for(sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SyncSessionLocal = sessionmaker(bind=sync_engine)


async def init_db() -> None:
    """Create all tables (idempotent)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """FastAPI dependency for async DB sessions."""
    async with AsyncSessionLocal() as session:
        yield session


def get_sync_db() -> Session:
    """Celery worker dependency for sync DB sessions."""
    return SyncSessionLocal()
