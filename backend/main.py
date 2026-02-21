"""
FastAPI application – IT Maturity Assessment MVP.

Endpoints:
  POST /api/assessments          – start a new assessment run
  GET  /api/assessments/{run_id} – get run status + artifact URLs
  GET  /api/assessments          – list recent runs
  GET  /artifacts/{run_id}/{file} – serve artifact files
  GET  /health                   – health check
"""
from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db import init_db, get_db, SyncSessionLocal
from backend.models import (
    AssessmentRequest, AssessmentRun, RunStatus, RunStatusResponse
)
from backend.storage.repository import (
    create_run, find_cached_run, get_run, update_run_status
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# FastAPI app
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="IT Maturity Assessment API",
    description="Automated IT maturity assessment using public data sources.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────────────────────
# In-memory rate limiter (per-IP)
# ──────────────────────────────────────────────────────────────────────────────

_rate_limit_store: Dict[str, List[float]] = defaultdict(list)


def check_rate_limit(ip: str) -> bool:
    """Returns True if request is allowed, False if rate limited."""
    now = time.time()
    window = settings.RATE_LIMIT_WINDOW_SECONDS
    timestamps = _rate_limit_store[ip]
    # Clean old entries
    _rate_limit_store[ip] = [t for t in timestamps if now - t < window]
    if len(_rate_limit_store[ip]) >= settings.RATE_LIMIT_PER_IP:
        return False
    _rate_limit_store[ip].append(now)
    return True


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ──────────────────────────────────────────────────────────────────────────────
# Startup / shutdown
# ──────────────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    await init_db()
    settings.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("IT Maturity Assessment API started. Mode: %s", settings.LLM_MODE)


# ──────────────────────────────────────────────────────────────────────────────
# Artifact file serving
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/artifacts/{run_id}/{filename}")
async def serve_artifact(run_id: str, filename: str):
    """Serve artifact files for a given run."""
    # Security: only allow safe filenames
    if not filename.replace(".", "").replace("_", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid filename")
    allowed_extensions = {".html", ".pdf", ".png", ".json"}
    suffix = Path(filename).suffix.lower()
    if suffix not in allowed_extensions:
        raise HTTPException(status_code=400, detail="File type not allowed")

    artifact_path = settings.ARTIFACTS_DIR / run_id / filename
    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")

    media_types = {
        ".html": "text/html",
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".json": "application/json",
    }
    return FileResponse(
        str(artifact_path),
        media_type=media_types.get(suffix, "application/octet-stream"),
    )


# ──────────────────────────────────────────────────────────────────────────────
# API endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "mode": settings.LLM_MODE, "search_provider": settings.SEARCH_PROVIDER}


@app.post("/api/assessments", response_model=RunStatusResponse)
async def create_assessment(
    request: Request,
    body: AssessmentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Start a new IT Maturity Assessment run."""
    ip = get_client_ip(request)
    if not check_rate_limit(ip):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {settings.RATE_LIMIT_PER_IP} requests per hour.",
        )

    # Check cache (sync DB call needed for simplicity)
    sync_db = SyncSessionLocal()
    try:
        cached = find_cached_run(
            sync_db,
            body.company_name,
            body.company_domain,
            settings.CACHE_TTL_DAYS,
        )
        if cached:
            logger.info("Returning cached run %s for %s", cached.id, body.company_name)
            return _run_to_response(cached, request)

        # Create new run
        run = create_run(
            sync_db,
            company_name=body.company_name,
            company_domain=body.company_domain,
            country=body.country,
        )
        run_id = str(run.id)
    finally:
        sync_db.close()

    # Dispatch Celery task
    try:
        from backend.tasks import run_assessment_task
        task = run_assessment_task.delay(
            run_id=run_id,
            company_name=body.company_name,
            company_domain=body.company_domain,
            country=body.country,
        )
        logger.info("Dispatched task %s for run %s", task.id, run_id)

        # Store task ID
        sync_db2 = SyncSessionLocal()
        try:
            r = sync_db2.query(AssessmentRun).filter(AssessmentRun.id == run_id).first()
            if r:
                r.celery_task_id = task.id
                sync_db2.commit()
        finally:
            sync_db2.close()

    except Exception as exc:
        logger.error("Failed to dispatch task: %s", exc)
        # Fallback: run inline (for environments without Celery)
        sync_db3 = SyncSessionLocal()
        try:
            _run_inline(run_id, body.company_name, body.company_domain, body.country, sync_db3)
        finally:
            sync_db3.close()

    # Return initial status
    sync_db4 = SyncSessionLocal()
    try:
        run = sync_db4.query(AssessmentRun).filter(AssessmentRun.id == run_id).first()
        return _run_to_response(run, request)
    finally:
        sync_db4.close()


@app.get("/api/assessments/{run_id}", response_model=RunStatusResponse)
async def get_assessment_status(run_id: str, request: Request):
    """Get the status and artifacts for a run."""
    sync_db = SyncSessionLocal()
    try:
        run = sync_db.query(AssessmentRun).filter(AssessmentRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return _run_to_response(run, request)
    finally:
        sync_db.close()


@app.get("/api/assessments")
async def list_assessments(limit: int = 20):
    """List recent assessment runs."""
    sync_db = SyncSessionLocal()
    try:
        runs = (
            sync_db.query(AssessmentRun)
            .order_by(AssessmentRun.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "run_id": str(r.id),
                "company_name": r.company_name,
                "status": r.status.value,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in runs
        ]
    finally:
        sync_db.close()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

STATUS_MESSAGES = {
    RunStatus.PENDING: "Assessment queued…",
    RunStatus.COLLECTING: "Collecting public sources…",
    RunStatus.ANALYZING: "Analyzing evidence…",
    RunStatus.RENDERING: "Rendering report…",
    RunStatus.COMPLETE: "Assessment complete.",
    RunStatus.FAILED: "Assessment failed.",
}


def _make_artifact_url(request: Request, run_id: str, filename: Optional[str]) -> Optional[str]:
    if not filename:
        return None
    base = str(request.base_url).rstrip("/")
    return f"{base}/artifacts/{run_id}/{Path(filename).name}"


def _run_to_response(run: AssessmentRun, request: Request) -> RunStatusResponse:
    run_id = str(run.id)
    return RunStatusResponse(
        run_id=run_id,
        status=run.status,
        company_name=run.company_name,
        created_at=run.created_at,
        updated_at=run.updated_at,
        completed_at=run.completed_at,
        error_message=run.error_message,
        report_url=_make_artifact_url(request, run_id, run.report_html_path),
        maturity_visual_url=_make_artifact_url(request, run_id, run.maturity_visual_path),
        key_takeaways_url=_make_artifact_url(request, run_id, run.key_takeaways_path),
        progress_message=STATUS_MESSAGES.get(run.status, ""),
    )


def _run_inline(
    run_id: str,
    company_name: str,
    company_domain: Optional[str],
    country: Optional[str],
    db,
) -> None:
    """Fallback: run pipeline inline (no Celery)."""
    import asyncio
    from backend.orchestrator import run_pipeline

    logger.info("Running pipeline inline for run %s", run_id)
    try:
        asyncio.run(
            run_pipeline(
                run_id=run_id,
                company_name=company_name,
                company_domain=company_domain,
                country=country,
                db=db,
            )
        )
    except Exception as exc:
        logger.error("Inline pipeline failed: %s", exc)


# ──────────────────────────────────────────────────────────────────────────────
# Serve frontend static files
# ──────────────────────────────────────────────────────────────────────────────

frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
