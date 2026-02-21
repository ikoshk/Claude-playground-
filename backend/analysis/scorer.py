"""
Deterministic Scoring Engine.

Decides FINAL maturity for each Q1–Q15 based on:
- LLM proposal
- Evidence window validation (2023–2025 only)
- Primary source requirements
- Independent source requirements
- Evidence count thresholds per rubric

The LLM NEVER decides final maturity – only proposes.
"""
from __future__ import annotations

import logging
import math
import statistics
from typing import Dict, List, Optional, Tuple

from backend.analysis.rubric import (
    RUBRIC, DIMENSION_QUESTION_MAP, DIMENSION_NAMES,
    RUBRIC_BY_ID
)
from backend.collectors.crawler import is_in_window, is_primary_source
from backend.models import (
    CitationItem, ConfidenceLevel, DimensionResult, LLMExtractionResult,
    MaturityLevel, MATURITY_NUMERIC, MATURITY_FROM_NUMERIC,
    QuestionResult, ReportData
)

logger = logging.getLogger(__name__)

MATURITY_ORDER = [
    MaturityLevel.INITIAL,
    MaturityLevel.IN_DEVELOPMENT,
    MaturityLevel.INDUSTRIALIZED,
    MaturityLevel.STATE_OF_THE_ART,
]

MATURITY_INDEX = {m: i for i, m in enumerate(MATURITY_ORDER)}


# ──────────────────────────────────────────────────────────────────────────────
# Source classification helpers
# ──────────────────────────────────────────────────────────────────────────────

def classify_source(citation: CitationItem, company_domain: Optional[str]) -> Dict:
    """Classify a citation as primary, independent, etc."""
    url = citation.url or ""
    domain_parts = set()
    try:
        from urllib.parse import urlparse
        netloc = urlparse(url).netloc.lower().replace("www.", "")
        domain_parts.add(netloc.split(".")[0] if netloc else "")
    except Exception:
        pass

    primary = is_primary_source(url, company_domain)
    in_window = is_in_window(citation.published_date)

    # Classify source type
    source_type = "independent"
    if primary:
        source_type = "primary"
    url_lower = url.lower()
    if any(x in url_lower for x in [".pdf", "annualreport", "annual-report", "ir.", "investor"]):
        source_type = "primary"
    if any(x in url_lower for x in ["esg", "sustainability", "csr"]):
        source_type = "esg"
    if any(x in url_lower for x in ["linkedin.com/jobs", "/careers/", "/jobs/"]):
        source_type = "job_posting"
    if any(x in url_lower for x in ["gartner", "forrester", "idc.com"]):
        source_type = "industry"
    if any(x in url_lower for x in ["cyber", "security", "sans.org"]):
        source_type = "cyber"

    return {
        "is_primary": primary or source_type == "primary",
        "is_in_window": in_window,
        "source_type": source_type,
        "domain": domain_parts.pop() if domain_parts else "",
    }


def count_independent_domains(citations: List[CitationItem], company_domain: Optional[str]) -> int:
    """Count distinct root domains (independent sources)."""
    domains = set()
    for c in citations:
        try:
            from urllib.parse import urlparse
            netloc = urlparse(c.url or "").netloc.lower().replace("www.", "")
            if netloc:
                domains.add(netloc)
        except Exception:
            pass
    return len(domains)


# ──────────────────────────────────────────────────────────────────────────────
# Evidence validation
# ──────────────────────────────────────────────────────────────────────────────

def validate_evidence_for_level(
    proposed_level: MaturityLevel,
    in_window_citations: List[CitationItem],
    company_domain: Optional[str],
    question: Dict,
) -> Tuple[MaturityLevel, bool]:
    """
    Check if evidence meets requirements for the proposed maturity level.
    Returns (allowed_level, was_downgraded).
    Walks down from proposed_level until requirements are met.
    """
    # Classify all in-window citations
    classified = [classify_source(c, company_domain) for c in in_window_citations]
    has_primary = any(c["is_primary"] for c in classified)
    num_independent = count_independent_domains(in_window_citations, company_domain)
    num_sources = len(in_window_citations)

    # Try to satisfy from highest to lowest
    level_idx = MATURITY_INDEX[proposed_level]

    while level_idx >= 0:
        level = MATURITY_ORDER[level_idx]
        reqs = question["evidence_requirements"].get(level.value, {})
        min_sources = reqs.get("min_sources", 0)
        source_types = reqs.get("source_types", [])

        ok = True
        if num_sources < min_sources:
            ok = False
        if ok and "primary" in source_types and not has_primary:
            ok = False
        if ok and "independent" in source_types and num_independent < 2:
            ok = False

        if ok:
            downgraded = level != proposed_level
            return level, downgraded

        level_idx -= 1

    # Nothing satisfies – default to Initial
    return MaturityLevel.INITIAL, proposed_level != MaturityLevel.INITIAL


# ──────────────────────────────────────────────────────────────────────────────
# Confidence calculation
# ──────────────────────────────────────────────────────────────────────────────

def compute_confidence(
    num_in_window: int, has_primary: bool, data_gap: bool
) -> ConfidenceLevel:
    if data_gap or num_in_window == 0:
        return ConfidenceLevel.LOW
    if num_in_window >= 2 and has_primary:
        return ConfidenceLevel.HIGH
    if num_in_window >= 1:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


# ──────────────────────────────────────────────────────────────────────────────
# Score a single question
# ──────────────────────────────────────────────────────────────────────────────

def score_question(
    llm_result: LLMExtractionResult,
    all_in_window_citations: List[CitationItem],
    company_domain: Optional[str],
) -> QuestionResult:
    """Apply deterministic scoring rules to produce a final QuestionResult."""
    question = RUBRIC_BY_ID[llm_result.question_id]

    # Merge citations from LLM result + any we have from collection
    # Filter to in-window only
    combined_citations = list(llm_result.citations)
    seen_urls = {c.url for c in combined_citations}
    for c in all_in_window_citations:
        if c.url not in seen_urls:
            combined_citations.append(c)
            seen_urls.add(c.url)

    in_window = [c for c in combined_citations if is_in_window(c.published_date)]

    # If data gap flagged or no in-window sources: default to Initial
    if llm_result.data_gap_flag or not in_window:
        return QuestionResult(
            question_id=question["question_id"],
            dimension_id=question["dimension_id"],
            sub_dimension=question["sub_dimension"],
            question_text=question["question_text"],
            final_maturity=MaturityLevel.INITIAL,
            maturity_numeric=MATURITY_NUMERIC[MaturityLevel.INITIAL],
            justification="Insufficient public data to assess beyond baseline.",
            confidence=ConfidenceLevel.LOW,
            citations=[],
            extracted_signals=llm_result.extracted_signals,
            data_gap=True,
            downgraded=llm_result.maturity_proposal != MaturityLevel.INITIAL,
        )

    # Validate and potentially downgrade
    final_level, downgraded = validate_evidence_for_level(
        llm_result.maturity_proposal, in_window, company_domain, question
    )

    classified = [classify_source(c, company_domain) for c in in_window]
    has_primary = any(c["is_primary"] for c in classified)
    confidence = compute_confidence(len(in_window), has_primary, llm_result.data_gap_flag)

    # Adjust justification if downgraded
    justification = llm_result.justification
    if downgraded:
        justification = (
            f"[Downgraded from {llm_result.maturity_proposal.value}] "
            f"Evidence requirements not met. {justification}"
        )[:500]

    return QuestionResult(
        question_id=question["question_id"],
        dimension_id=question["dimension_id"],
        sub_dimension=question["sub_dimension"],
        question_text=question["question_text"],
        final_maturity=final_level,
        maturity_numeric=MATURITY_NUMERIC[final_level],
        justification=justification,
        confidence=confidence,
        citations=in_window[:5],  # cap displayed citations
        extracted_signals=llm_result.extracted_signals,
        data_gap=llm_result.data_gap_flag,
        downgraded=downgraded,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Dimension aggregation
# ──────────────────────────────────────────────────────────────────────────────

def aggregate_dimension(
    dimension_id: str,
    question_results: List[QuestionResult],
) -> DimensionResult:
    """
    Aggregate question results into a dimension result.
    Dimension maturity = rounded median of question numerics.
    """
    numerics = [q.maturity_numeric for q in question_results]
    median_val = statistics.median(numerics) if numerics else 1.0
    rounded = round(median_val)
    # Clamp to 1–4
    rounded = max(1, min(4, rounded))
    dim_maturity = MATURITY_FROM_NUMERIC[rounded]

    # Confidence = lowest confidence among questions
    conf_order = {ConfidenceLevel.LOW: 0, ConfidenceLevel.MEDIUM: 1, ConfidenceLevel.HIGH: 2}
    min_conf = min(question_results, key=lambda q: conf_order[q.confidence]).confidence

    # Identify strengths (Industrialized+) and weaknesses (Initial/In dev)
    strengths = []
    weaknesses = []
    recommendations = []
    for q in question_results:
        if q.final_maturity in (MaturityLevel.INDUSTRIALIZED, MaturityLevel.STATE_OF_THE_ART):
            strengths.append(f"{q.sub_dimension}: {q.final_maturity.value}")
        else:
            weaknesses.append(f"{q.sub_dimension}: {q.final_maturity.value}")
            recommendations.append(
                f"Improve {q.sub_dimension} from {q.final_maturity.value} level."
            )

    return DimensionResult(
        dimension_id=dimension_id,
        dimension_name=DIMENSION_NAMES[dimension_id],
        maturity=dim_maturity,
        maturity_numeric=round(median_val, 2),
        confidence=min_conf,
        questions=question_results,
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recommendations[:3],  # cap at 3 per dimension
    )


# ──────────────────────────────────────────────────────────────────────────────
# Key takeaway generation
# ──────────────────────────────────────────────────────────────────────────────

def generate_key_takeaways(dimension_results: List[DimensionResult]) -> List[Dict]:
    """
    Generate up to 5 key takeaways based on lowest-scoring areas.
    Each takeaway needs at least 1 in-window citation.
    """
    # Collect weakest questions
    weak_questions = []
    for dim in dimension_results:
        for q in dim.questions:
            if q.final_maturity in (MaturityLevel.INITIAL, MaturityLevel.IN_DEVELOPMENT):
                weak_questions.append((q, dim))

    # Sort by maturity (weakest first), then by question ID
    weak_questions.sort(key=lambda x: (x[0].maturity_numeric, x[0].question_id))

    takeaways = []
    for q, dim in weak_questions[:5]:
        citations = [c for c in q.citations if is_in_window(c.published_date)]
        if not citations and not q.data_gap:
            # Try to find any citation
            citations = q.citations[:1]

        title = f"Strengthen {q.sub_dimension} in {dim.dimension_name}"
        just = q.justification[:200]  # <=30 words enforced in validator
        # Trim to 30 words
        words = just.split()
        if len(words) > 30:
            just = " ".join(words[:30]) + "..."

        takeaways.append(
            {
                "title": title,
                "justification": just,
                "citations": [c.dict() for c in citations[:2]],
            }
        )

    # If all dimensions are strong, pick top improvement areas
    if not takeaways:
        for dim in dimension_results:
            if len(takeaways) >= 5:
                break
            for q in dim.questions:
                if len(takeaways) >= 5:
                    break
                citations = q.citations[:1]
                takeaways.append(
                    {
                        "title": f"Advance {q.sub_dimension} to next maturity level",
                        "justification": f"{q.sub_dimension} is at {q.final_maturity.value}; further advancement recommended.",
                        "citations": [c.dict() for c in citations],
                    }
                )

    return takeaways[:5]


# ──────────────────────────────────────────────────────────────────────────────
# Full scoring pipeline
# ──────────────────────────────────────────────────────────────────────────────

def run_scoring(
    llm_results: Dict[str, LLMExtractionResult],
    all_citations_by_question: Dict[str, List[CitationItem]],
    company_domain: Optional[str],
    run_id: str,
    company_name: str,
    country: Optional[str] = None,
) -> ReportData:
    """
    Run full deterministic scoring and produce ReportData.
    """
    from datetime import datetime

    # Score each question
    question_results_by_id: Dict[str, QuestionResult] = {}
    for q in RUBRIC:
        qid = q["question_id"]
        llm_res = llm_results.get(qid)
        if not llm_res:
            # Missing LLM result → default to Initial
            from backend.models import LLMExtractionResult as LLMRes
            llm_res = LLMRes(
                question_id=qid,
                maturity_proposal=MaturityLevel.INITIAL,
                justification="Insufficient public data to assess beyond baseline.",
                citations=[],
                extracted_signals=[],
                data_gap_flag=True,
            )
        in_window_cits = all_citations_by_question.get(qid, [])
        question_results_by_id[qid] = score_question(llm_res, in_window_cits, company_domain)

    # Aggregate by dimension
    dimension_results = []
    for dim_id, question_ids in DIMENSION_QUESTION_MAP.items():
        q_results = [question_results_by_id[qid] for qid in question_ids if qid in question_results_by_id]
        dim_result = aggregate_dimension(dim_id, q_results)
        dimension_results.append(dim_result)

    # Overall maturity (median of dimension numerics)
    dim_numerics = [d.maturity_numeric for d in dimension_results]
    overall_numeric = statistics.median(dim_numerics) if dim_numerics else 1.0
    overall_numeric_rounded = max(1, min(4, round(overall_numeric)))
    overall_maturity = MATURITY_FROM_NUMERIC[overall_numeric_rounded]

    # Key takeaways
    takeaway_dicts = generate_key_takeaways(dimension_results)
    from backend.models import KeyTakeaway
    takeaways = []
    for td in takeaway_dicts:
        cit_items = []
        for c in td.get("citations", []):
            cit_items.append(CitationItem(**c) if isinstance(c, dict) else c)
        takeaways.append(
            KeyTakeaway(
                title=td["title"],
                justification=td["justification"],
                citations=cit_items,
            )
        )

    # Build bibliography (all unique cited URLs)
    seen_urls: set = set()
    bibliography: List[CitationItem] = []
    for qr in question_results_by_id.values():
        for c in qr.citations:
            if c.url and c.url not in seen_urls:
                seen_urls.add(c.url)
                bibliography.append(c)
    for ta in takeaways:
        for c in ta.citations:
            if c.url and c.url not in seen_urls:
                seen_urls.add(c.url)
                bibliography.append(c)

    # Count sources
    all_citation_lists = list(all_citations_by_question.values())
    all_citations_flat = [c for lst in all_citation_lists for c in lst]
    in_window_count = sum(1 for c in all_citations_flat if is_in_window(c.published_date))

    return ReportData(
        run_id=run_id,
        company_name=company_name,
        company_domain=company_domain,
        country=country,
        generated_at=datetime.utcnow(),
        dimensions=dimension_results,
        overall_maturity=overall_maturity,
        overall_maturity_numeric=round(overall_numeric, 2),
        key_takeaways=takeaways,
        bibliography=bibliography,
        validator_passed=False,  # Set by validator
        sources_collected=len(all_citations_flat),
        sources_in_window=in_window_count,
    )
