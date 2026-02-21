"""
Pipeline Orchestrator – runs the complete IT Maturity Assessment pipeline.

Pipeline stages:
1. Evidence Collection (search + crawl)
2. Evidence Filtering (recency + dedup)
3. LLM Extraction (structured signals)
4. Deterministic Scoring
5. Validation
6. Report Rendering (HTML + PDF + images)
7. Artifact Persistence
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from backend.analysis.extractor import extract_all_questions
from backend.analysis.rubric import RUBRIC, get_all_search_queries
from backend.analysis.scorer import run_scoring
from backend.analysis.validator import build_dimension_summary_cells, validate_report
from backend.collectors.base import SearchResult
from backend.collectors.crawler import (
    compute_content_hash, fetch_page, is_in_window, is_primary_source
)
from backend.collectors.pdf import fetch_pdf
from backend.collectors.search_provider import get_search_provider
from backend.config import settings
from backend.models import (
    AssessmentRun, CitationItem, LLMExtractionResult, MaturityLevel,
    ReportData, RunStatus
)
from backend.rendering.renderer import render_html, render_pdf
from backend.rendering.visuals import generate_key_takeaways_visual, generate_maturity_visual
from backend.storage.repository import (
    run_artifacts_dir, save_evidence_sources, save_raw_text, save_report_json,
    update_run_artifacts, update_run_status
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Status callback type
# ──────────────────────────────────────────────────────────────────────────────

StatusCallback = Optional[callable]  # (status: RunStatus, msg: str) -> None


# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 & 2: Evidence collection + filtering
# ──────────────────────────────────────────────────────────────────────────────

async def collect_evidence(
    company_name: str,
    company_domain: Optional[str],
    run_id: str,
) -> Tuple[List[Dict], Dict[str, List[Dict]]]:
    """
    Collect and filter evidence sources.
    Returns:
      - all_sources: list of source dicts (all collected)
      - evidence_map: {question_id: [in-window source dicts]}
    """
    search_provider = get_search_provider()
    queries = get_all_search_queries(company_name, company_domain)

    # ── Search phase ─────────────────────────────────────────────────────────
    logger.info("[%s] Running %d search queries via %s", run_id, len(queries), search_provider.name)
    search_results: List[SearchResult] = []
    seen_urls: Set[str] = set()

    for q_info in queries:
        if len(seen_urls) >= settings.MAX_URLS_PER_RUN:
            break
        try:
            results = await search_provider.search(q_info["query"], num_results=5)
            for r in results:
                if r.url and r.url not in seen_urls:
                    seen_urls.add(r.url)
                    r.question_id = q_info["question_id"]
                    search_results.append(r)
        except Exception as exc:
            logger.warning("[%s] Search failed for %r: %s", run_id, q_info["query"], exc)

    logger.info("[%s] Got %d unique URLs from search", run_id, len(search_results))

    # ── Fetch + extract phase ────────────────────────────────────────────────
    all_sources: List[Dict] = []
    content_hashes: Set[str] = set()

    # Process in batches to avoid overwhelming targets
    batch_size = 8
    for i in range(0, len(search_results), batch_size):
        batch = search_results[i : i + batch_size]
        tasks = []
        for sr in batch:
            if sr.url.lower().endswith(".pdf"):
                tasks.append(_fetch_and_process_pdf(sr, run_id, company_domain))
            else:
                tasks.append(_fetch_and_process_page(sr, run_id, company_domain))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for sr, res in zip(batch, results):
            if isinstance(res, Exception):
                logger.debug("[%s] Fetch error for %s: %s", run_id, sr.url, res)
                continue
            if res is None:
                # Use snippet from search result as fallback
                res = _make_snippet_source(sr, company_domain)
            if res:
                # Dedup by content hash
                ch = res.get("content_hash") or compute_content_hash(res.get("text", ""))
                if ch in content_hashes:
                    continue
                content_hashes.add(ch)
                all_sources.append(res)

    logger.info("[%s] Collected %d unique sources", run_id, len(all_sources))

    # ── Filter to in-window ──────────────────────────────────────────────────
    in_window_sources = [s for s in all_sources if is_in_window(s.get("published_date"))]
    out_of_window = [s for s in all_sources if not is_in_window(s.get("published_date"))]

    logger.info(
        "[%s] In-window: %d, Out-of-window: %d",
        run_id, len(in_window_sources), len(out_of_window),
    )

    # ── Build coverage map: question → in-window sources ────────────────────
    evidence_map: Dict[str, List[Dict]] = {q["question_id"]: [] for q in RUBRIC}

    for src in in_window_sources:
        matched_questions = src.get("questions_matched", [])
        for qid in matched_questions:
            if qid in evidence_map:
                evidence_map[qid].append(src)

    # Fallback: if a question has no direct matches, try signal-based matching
    for q in RUBRIC:
        qid = q["question_id"]
        if not evidence_map[qid]:
            signals = [s.lower() for s in q["mapped_signals"]]
            for src in in_window_sources:
                text_lower = (src.get("text", "") + src.get("title", "")).lower()
                if any(sig in text_lower for sig in signals):
                    evidence_map[qid].append(src)

    return all_sources, evidence_map


def _make_snippet_source(sr: SearchResult, company_domain: Optional[str]) -> Optional[Dict]:
    """Create a lightweight source dict from a search snippet (fallback)."""
    if not sr.snippet:
        return None
    return {
        "url": sr.url,
        "title": sr.title,
        "text": sr.snippet,
        "published_date": sr.published_date,
        "date_confidence": "approximate" if sr.published_date else "unknown",
        "content_hash": compute_content_hash(sr.snippet),
        "source_type": "snippet",
        "is_primary_source": is_primary_source(sr.url, company_domain),
        "in_window": is_in_window(sr.published_date),
        "questions_matched": [sr.question_id] if sr.question_id else [],
    }


async def _fetch_and_process_page(
    sr: SearchResult, run_id: str, company_domain: Optional[str]
) -> Optional[Dict]:
    """Fetch an HTML page and return a source dict."""
    page = await fetch_page(sr.url)
    if not page:
        return None

    # Override date with search provider's date if more reliable
    if not page.get("published_date") and sr.published_date:
        page["published_date"] = sr.published_date
        page["date_confidence"] = "approximate"

    page["is_primary_source"] = is_primary_source(sr.url, company_domain)
    page["in_window"] = is_in_window(page.get("published_date"))
    page["questions_matched"] = [sr.question_id] if sr.question_id else []

    # Save raw text artifact
    try:
        if page.get("text"):
            save_raw_text(run_id, sr.url, page["text"])
    except Exception:
        pass

    return page


async def _fetch_and_process_pdf(
    sr: SearchResult, run_id: str, company_domain: Optional[str]
) -> Optional[Dict]:
    """Fetch a PDF and return a source dict."""
    pdf_data = await fetch_pdf(sr.url)
    if not pdf_data:
        return None

    if not pdf_data.get("published_date") and sr.published_date:
        pdf_data["published_date"] = sr.published_date
        pdf_data["date_confidence"] = "approximate"

    pdf_data["is_primary_source"] = is_primary_source(sr.url, company_domain)
    pdf_data["in_window"] = is_in_window(pdf_data.get("published_date"))
    pdf_data["questions_matched"] = [sr.question_id] if sr.question_id else []

    try:
        if pdf_data.get("text"):
            save_raw_text(run_id, sr.url, pdf_data["text"])
    except Exception:
        pass

    return pdf_data


# ──────────────────────────────────────────────────────────────────────────────
# Stage 3: Build CitationItem map from evidence
# ──────────────────────────────────────────────────────────────────────────────

def build_citation_map(
    evidence_map: Dict[str, List[Dict]],
    company_domain: Optional[str],
) -> Dict[str, List[CitationItem]]:
    """Convert evidence_map dicts to CitationItem objects."""
    result: Dict[str, List[CitationItem]] = {}
    for qid, sources in evidence_map.items():
        citations = []
        for src in sources:
            if not src.get("url"):
                continue
            citations.append(
                CitationItem(
                    url=src["url"],
                    title=src.get("title"),
                    published_date=src.get("published_date"),
                    publisher=_extract_publisher(src["url"]),
                    is_primary=src.get("is_primary_source", False),
                )
            )
        result[qid] = citations
    return result


def _extract_publisher(url: str) -> Optional[str]:
    """Extract a simple publisher name from URL domain."""
    try:
        from urllib.parse import urlparse
        netloc = urlparse(url).netloc.lower().replace("www.", "")
        parts = netloc.split(".")
        if len(parts) >= 2:
            return parts[-2].capitalize()
    except Exception:
        pass
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Full pipeline runner
# ──────────────────────────────────────────────────────────────────────────────

async def run_pipeline(
    run_id: str,
    company_name: str,
    company_domain: Optional[str],
    country: Optional[str],
    db,  # SQLAlchemy sync session
    status_callback: StatusCallback = None,
) -> ReportData:
    """
    Execute the complete assessment pipeline.
    Returns complete ReportData when done.
    Raises on critical failure.
    """

    def _status(status: RunStatus, msg: str):
        logger.info("[%s] %s: %s", run_id, status.value, msg)
        update_run_status(db, run_id, status)
        if status_callback:
            status_callback(status, msg)

    try:
        # ── Stage 1 & 2: Evidence Collection ─────────────────────────────────
        _status(RunStatus.COLLECTING, "Collecting public sources…")
        all_sources, evidence_map = await collect_evidence(company_name, company_domain, run_id)

        # Persist source metadata
        source_records = []
        for src in all_sources:
            source_records.append({
                **src,
                "text": None,  # don't store text in DB column
            })
        save_evidence_sources(db, run_id, source_records)

        # ── Stage 3: LLM Extraction ───────────────────────────────────────────
        _status(RunStatus.ANALYZING, "Extracting maturity signals…")
        llm_results: Dict[str, LLMExtractionResult] = await extract_all_questions(
            RUBRIC, evidence_map
        )

        # ── Stage 4: Deterministic Scoring ────────────────────────────────────
        citation_map = build_citation_map(evidence_map, company_domain)
        report = run_scoring(
            llm_results=llm_results,
            all_citations_by_question=citation_map,
            company_domain=company_domain,
            run_id=run_id,
            company_name=company_name,
            country=country,
        )

        # Add source counts
        report.sources_collected = len(all_sources)
        in_window_count = sum(1 for s in all_sources if is_in_window(s.get("published_date")))
        report.sources_in_window = in_window_count

        # ── Stage 5: Build summary cells + validate ───────────────────────────
        _status(RunStatus.RENDERING, "Building report…")
        report = build_dimension_summary_cells(report)
        passed, errors = validate_report(report)
        report.validator_passed = passed

        if not passed:
            logger.warning("[%s] Validator warnings: %s", run_id, errors)
            # Not a hard stop for MVP – log and continue

        # ── Stage 6: Render artifacts ─────────────────────────────────────────
        artifacts_dir = run_artifacts_dir(run_id)

        maturity_visual_path = artifacts_dir / "maturity_visual.png"
        key_takeaways_path = artifacts_dir / "key_takeaways.png"
        report_html_path = artifacts_dir / "report.html"
        report_pdf_path = artifacts_dir / "report.pdf"

        generate_maturity_visual(report.dimensions, maturity_visual_path, company_name)
        generate_key_takeaways_visual(report.key_takeaways, key_takeaways_path, company_name)

        render_html(report, report_html_path, maturity_visual_path, key_takeaways_path)

        pdf_path = None
        try:
            pdf_path = render_pdf(report_html_path, report_pdf_path)
        except Exception as exc:
            logger.warning("[%s] PDF render failed (non-critical): %s", run_id, exc)

        # ── Stage 7: Persist ──────────────────────────────────────────────────
        save_report_json(run_id, report)

        update_run_artifacts(
            db,
            run_id,
            report_html_path=str(report_html_path),
            report_pdf_path=str(pdf_path) if pdf_path else None,
            maturity_visual_path=str(maturity_visual_path),
            key_takeaways_path=str(key_takeaways_path),
            report_json=report.dict(),
        )

        _status(RunStatus.COMPLETE, "Assessment complete.")
        return report

    except Exception as exc:
        logger.error("[%s] Pipeline failed: %s", run_id, exc, exc_info=True)
        update_run_status(db, run_id, RunStatus.FAILED, str(exc))
        raise
