"""
Storage repository – persists run artifacts to filesystem + database.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import AssessmentRun, EvidenceSource, RunStatus, ReportData

logger = logging.getLogger(__name__)


def run_artifacts_dir(run_id: str) -> Path:
    """Return the artifact directory for a given run."""
    d = settings.ARTIFACTS_DIR / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_raw_text(run_id: str, url: str, text: str) -> Path:
    """Save raw extracted text for a source."""
    d = run_artifacts_dir(run_id) / "raw_texts"
    d.mkdir(parents=True, exist_ok=True)
    safe_name = url.replace("://", "_").replace("/", "_")[:100] + ".txt"
    path = d / safe_name
    path.write_text(text, encoding="utf-8")
    return path


def save_report_json(run_id: str, report: ReportData) -> Path:
    """Save the full ReportData as JSON."""
    d = run_artifacts_dir(run_id)
    path = d / "report.json"
    path.write_text(report.json(indent=2), encoding="utf-8")
    return path


def load_report_json(run_id: str) -> Optional[ReportData]:
    """Load ReportData from JSON artifact."""
    d = run_artifacts_dir(run_id)
    path = d / "report.json"
    if not path.exists():
        return None
    try:
        return ReportData.parse_raw(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Failed to load report JSON for run %s: %s", run_id, exc)
        return None


# ── Database helpers ──────────────────────────────────────────────────────────

def create_run(
    db: Session,
    company_name: str,
    company_domain: Optional[str],
    country: Optional[str],
) -> AssessmentRun:
    run = AssessmentRun(
        id=uuid.uuid4(),
        company_name=company_name,
        company_domain=company_domain,
        country=country,
        status=RunStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def update_run_status(
    db: Session,
    run_id: str,
    status: RunStatus,
    error_message: Optional[str] = None,
) -> None:
    run = db.query(AssessmentRun).filter(AssessmentRun.id == run_id).first()
    if not run:
        return
    run.status = status
    run.updated_at = datetime.utcnow()
    if error_message:
        run.error_message = error_message
    if status == RunStatus.COMPLETE:
        run.completed_at = datetime.utcnow()
    db.commit()


def update_run_artifacts(
    db: Session,
    run_id: str,
    report_html_path: Optional[str] = None,
    report_pdf_path: Optional[str] = None,
    maturity_visual_path: Optional[str] = None,
    key_takeaways_path: Optional[str] = None,
    report_json: Optional[Dict] = None,
) -> None:
    run = db.query(AssessmentRun).filter(AssessmentRun.id == run_id).first()
    if not run:
        return
    if report_html_path is not None:
        run.report_html_path = report_html_path
    if report_pdf_path is not None:
        run.report_pdf_path = report_pdf_path
    if maturity_visual_path is not None:
        run.maturity_visual_path = maturity_visual_path
    if key_takeaways_path is not None:
        run.key_takeaways_path = key_takeaways_path
    if report_json is not None:
        run.report_json = report_json
    run.updated_at = datetime.utcnow()
    db.commit()


def get_run(db: Session, run_id: str) -> Optional[AssessmentRun]:
    return db.query(AssessmentRun).filter(AssessmentRun.id == run_id).first()


def find_cached_run(
    db: Session,
    company_name: str,
    company_domain: Optional[str],
    max_age_days: int,
) -> Optional[AssessmentRun]:
    """Find a completed cached run for the same company within max_age_days."""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=max_age_days)
    return (
        db.query(AssessmentRun)
        .filter(
            AssessmentRun.company_name == company_name,
            AssessmentRun.status == RunStatus.COMPLETE,
            AssessmentRun.completed_at >= cutoff,
        )
        .order_by(AssessmentRun.completed_at.desc())
        .first()
    )


def save_evidence_sources(
    db: Session,
    run_id: str,
    sources: List[Dict],
) -> None:
    """Persist evidence source metadata to DB."""
    for src in sources:
        ev = EvidenceSource(
            id=uuid.uuid4(),
            run_id=run_id,
            url=src.get("url", ""),
            title=src.get("title"),
            publisher=src.get("publisher"),
            published_date=src.get("published_date"),
            date_confidence=src.get("date_confidence"),
            content_hash=src.get("content_hash"),
            in_window=src.get("in_window", True),
            is_primary_source=src.get("is_primary_source", False),
            source_type=src.get("source_type"),
            questions_matched=src.get("questions_matched", []),
        )
        db.add(ev)
    try:
        db.commit()
    except Exception as exc:
        logger.error("Failed to save evidence sources: %s", exc)
        db.rollback()
