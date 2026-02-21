"""
Celery task definitions for async pipeline execution.
"""
from __future__ import annotations

import asyncio
import logging

from celery import Celery

from backend.config import settings

logger = logging.getLogger(__name__)

# ── Celery app ────────────────────────────────────────────────────────────────
celery_app = Celery(
    "itmaturity",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "backend.tasks.run_assessment_task": {"queue": "assessments"},
    },
)


@celery_app.task(
    name="backend.tasks.run_assessment_task",
    bind=True,
    max_retries=0,  # No retries – one complete run
    soft_time_limit=600,  # 10 minutes soft limit
    time_limit=720,        # 12 minutes hard limit
)
def run_assessment_task(
    self,
    run_id: str,
    company_name: str,
    company_domain: str | None,
    country: str | None,
) -> dict:
    """
    Main Celery task: runs the full pipeline for one assessment.
    Returns minimal status dict; full report is in DB + filesystem.
    """
    from backend.db import get_sync_db
    from backend.orchestrator import run_pipeline
    from backend.models import RunStatus
    from backend.storage.repository import update_run_status

    db = get_sync_db()
    try:
        # Update Celery task ID on the run record
        from backend.storage.repository import get_run
        run = get_run(db, run_id)
        if run:
            run.celery_task_id = self.request.id
            db.commit()

        # Run pipeline (async via asyncio.run)
        report = asyncio.run(
            run_pipeline(
                run_id=run_id,
                company_name=company_name,
                company_domain=company_domain,
                country=country,
                db=db,
            )
        )
        return {
            "run_id": run_id,
            "status": "complete",
            "overall_maturity": report.overall_maturity.value,
        }

    except Exception as exc:
        logger.error("Assessment task failed for run %s: %s", run_id, exc, exc_info=True)
        update_run_status(db, run_id, RunStatus.FAILED, str(exc))
        raise
    finally:
        db.close()
