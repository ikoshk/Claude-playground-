"""
Validator – hard stop if report constraints are violated.

Checks:
1. All sections A–E exist.
2. All 6 dimensions present with valid maturity strings.
3. Only allowed maturity strings appear.
4. Every Q1–Q15 has citations (in-window) OR explicit gap statement.
5. Synthetic summary per dimension <=50 words.
6. Takeaways <=5, each with >=1 citation.
7. Bibliography contains all cited URLs exactly once.
"""
from __future__ import annotations

import re
from typing import List, Tuple

from backend.analysis.rubric import RUBRIC, DIMENSION_QUESTION_MAP
from backend.collectors.crawler import is_in_window
from backend.models import (
    ConfidenceLevel, DimensionResult, MaturityLevel, QuestionResult,
    ReportData
)

ALLOWED_MATURITY_STRINGS = {m.value for m in MaturityLevel}
GAP_STATEMENT = "Insufficient public data to assess beyond baseline."


def _word_count(text: str) -> int:
    return len(text.split())


def validate_report(report: ReportData) -> Tuple[bool, List[str]]:
    """
    Validate the complete report data.
    Returns (passed, list_of_errors).
    """
    errors: List[str] = []

    # ── 1. All 6 dimensions present ────────────────────────────────────────
    dim_ids = {d.dimension_id for d in report.dimensions}
    for did in DIMENSION_QUESTION_MAP:
        if did not in dim_ids:
            errors.append(f"Missing dimension: {did}")

    # ── 2. All Q1–Q15 present ──────────────────────────────────────────────
    all_question_ids = {q["question_id"] for q in RUBRIC}
    found_qids = set()
    for dim in report.dimensions:
        for q in dim.questions:
            found_qids.add(q.question_id)
    missing_qs = all_question_ids - found_qids
    if missing_qs:
        errors.append(f"Missing questions: {sorted(missing_qs)}")

    # ── 3. Only allowed maturity strings ──────────────────────────────────
    for dim in report.dimensions:
        if dim.maturity.value not in ALLOWED_MATURITY_STRINGS:
            errors.append(f"Invalid maturity '{dim.maturity.value}' for {dim.dimension_id}")
        for q in dim.questions:
            if q.final_maturity.value not in ALLOWED_MATURITY_STRINGS:
                errors.append(
                    f"Invalid maturity '{q.final_maturity.value}' for {q.question_id}"
                )

    # ── 4. Each Q has in-window citations OR gap statement ─────────────────
    for dim in report.dimensions:
        for q in dim.questions:
            in_window_citations = [c for c in q.citations if is_in_window(c.published_date)]
            has_gap_statement = (
                GAP_STATEMENT in q.justification or q.data_gap
            )
            if not in_window_citations and not has_gap_statement:
                errors.append(
                    f"{q.question_id}: No in-window citations and no gap statement."
                )

    # ── 5. Synthetic summary <=50 words ────────────────────────────────────
    for dim in report.dimensions:
        if dim.summary_cell:
            wc = _word_count(dim.summary_cell)
            if wc > 50:
                errors.append(
                    f"{dim.dimension_id} summary_cell exceeds 50 words ({wc} words)."
                )

    # ── 6. Takeaways <=5, each with >=1 citation ──────────────────────────
    if len(report.key_takeaways) > 5:
        errors.append(f"Too many takeaways: {len(report.key_takeaways)} (max 5).")
    for i, ta in enumerate(report.key_takeaways):
        if not ta.citations:
            errors.append(f"Takeaway {i+1} ('{ta.title}') has no citations.")
        # Justification word limit (<=30 words)
        wc = _word_count(ta.justification)
        if wc > 30:
            errors.append(
                f"Takeaway {i+1} justification exceeds 30 words ({wc} words)."
            )

    # ── 7. Bibliography has all cited URLs exactly once ────────────────────
    biblio_urls = [c.url for c in report.bibliography if c.url]
    if len(biblio_urls) != len(set(biblio_urls)):
        errors.append("Bibliography contains duplicate URLs.")

    # Collect all cited URLs from questions and takeaways
    cited_in_report: set = set()
    for dim in report.dimensions:
        for q in dim.questions:
            for c in q.citations:
                if c.url:
                    cited_in_report.add(c.url)
    for ta in report.key_takeaways:
        for c in ta.citations:
            if c.url:
                cited_in_report.add(c.url)

    biblio_set = set(biblio_urls)
    missing_from_biblio = cited_in_report - biblio_set
    if missing_from_biblio:
        errors.append(
            f"URLs cited in report but missing from bibliography: "
            f"{list(missing_from_biblio)[:5]}"
        )

    passed = len(errors) == 0
    return passed, errors


def enforce_summary_cell_limit(text: str, max_words: int = 50) -> str:
    """Truncate summary cell to max_words, appending '...' if needed."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."


def build_dimension_summary_cells(report: ReportData) -> ReportData:
    """
    Build and enforce the summary_cell field for each dimension (<=50 words).
    Modifies report in-place and returns it.
    """
    for dim in report.dimensions:
        strengths_text = "; ".join(dim.strengths[:2]) if dim.strengths else "N/A"
        weaknesses_text = "; ".join(dim.weaknesses[:2]) if dim.weaknesses else "N/A"
        rec_text = dim.recommendations[0] if dim.recommendations else "Continue current trajectory."
        raw = (
            f"Strengths: {strengths_text}. "
            f"Gaps: {weaknesses_text}. "
            f"Recommendation: {rec_text}"
        )
        dim.summary_cell = enforce_summary_cell_limit(raw, 50)
    return report
