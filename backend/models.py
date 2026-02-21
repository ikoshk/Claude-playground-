"""
Pydantic + SQLAlchemy models for the IT Maturity Assessment MVP.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean,
    DateTime, Enum as SAEnum, JSON, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# ──────────────────────────────────────────────────────────────────────────────
# Enumerations
# ──────────────────────────────────────────────────────────────────────────────

class MaturityLevel(str, enum.Enum):
    INITIAL = "Initial"
    IN_DEVELOPMENT = "In development"
    INDUSTRIALIZED = "Industrialized"
    STATE_OF_THE_ART = "State of the art"

MATURITY_NUMERIC: Dict[MaturityLevel, int] = {
    MaturityLevel.INITIAL: 1,
    MaturityLevel.IN_DEVELOPMENT: 2,
    MaturityLevel.INDUSTRIALIZED: 3,
    MaturityLevel.STATE_OF_THE_ART: 4,
}

MATURITY_FROM_NUMERIC: Dict[int, MaturityLevel] = {v: k for k, v in MATURITY_NUMERIC.items()}

class RunStatus(str, enum.Enum):
    PENDING = "pending"
    COLLECTING = "collecting"
    ANALYZING = "analyzing"
    RENDERING = "rendering"
    COMPLETE = "complete"
    FAILED = "failed"

class ConfidenceLevel(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

# ──────────────────────────────────────────────────────────────────────────────
# SQLAlchemy ORM models
# ──────────────────────────────────────────────────────────────────────────────

class AssessmentRun(Base):
    __tablename__ = "assessment_runs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = Column(String(255), nullable=False)
    company_domain = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    status = Column(SAEnum(RunStatus), default=RunStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    celery_task_id = Column(String(255), nullable=True)

    # Artifact paths (relative to ARTIFACTS_DIR)
    report_html_path = Column(String(512), nullable=True)
    report_pdf_path = Column(String(512), nullable=True)
    maturity_visual_path = Column(String(512), nullable=True)
    key_takeaways_path = Column(String(512), nullable=True)

    # Full report JSON for re-rendering
    report_json = Column(JSON, nullable=True)

    sources = relationship("EvidenceSource", back_populates="run", cascade="all, delete-orphan")


class EvidenceSource(Base):
    __tablename__ = "evidence_sources"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(PGUUID(as_uuid=True), ForeignKey("assessment_runs.id"), nullable=False)
    url = Column(Text, nullable=False)
    title = Column(Text, nullable=True)
    publisher = Column(Text, nullable=True)
    published_date = Column(String(20), nullable=True)  # YYYY-MM-DD or YYYY-MM or YYYY
    date_confidence = Column(String(20), nullable=True)  # exact / approximate / unknown
    content_hash = Column(String(64), nullable=True)
    raw_text_path = Column(String(512), nullable=True)
    in_window = Column(Boolean, default=True)
    is_primary_source = Column(Boolean, default=False)
    source_type = Column(String(50), nullable=True)  # pdf / html / job_posting / vendor_case_study
    questions_matched = Column(JSON, nullable=True)  # list of question ids

    run = relationship("AssessmentRun", back_populates="sources")

# ──────────────────────────────────────────────────────────────────────────────
# Pydantic request / response schemas
# ──────────────────────────────────────────────────────────────────────────────

class AssessmentRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    company_domain: Optional[str] = Field(None, max_length=255)
    country: Optional[str] = Field(None, max_length=100)


class RunStatusResponse(BaseModel):
    run_id: str
    status: RunStatus
    company_name: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    report_url: Optional[str] = None
    maturity_visual_url: Optional[str] = None
    key_takeaways_url: Optional[str] = None
    progress_message: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Internal pipeline data structures (not stored directly in DB columns)
# ──────────────────────────────────────────────────────────────────────────────

class CitationItem(BaseModel):
    url: str
    title: Optional[str] = None
    published_date: Optional[str] = None  # YYYY-MM-DD
    publisher: Optional[str] = None
    is_primary: bool = False

class LLMExtractionResult(BaseModel):
    """Strict JSON schema the LLM must output per question."""
    question_id: str
    maturity_proposal: MaturityLevel
    justification: str = Field(..., max_length=500)
    citations: List[CitationItem] = Field(default_factory=list)
    extracted_signals: List[str] = Field(default_factory=list)
    data_gap_flag: bool = False

class QuestionResult(BaseModel):
    question_id: str
    dimension_id: str
    sub_dimension: str
    question_text: str
    final_maturity: MaturityLevel
    maturity_numeric: int
    justification: str
    confidence: ConfidenceLevel
    citations: List[CitationItem] = Field(default_factory=list)
    extracted_signals: List[str] = Field(default_factory=list)
    data_gap: bool = False
    downgraded: bool = False  # True if scorer downgraded LLM proposal

class DimensionResult(BaseModel):
    dimension_id: str
    dimension_name: str
    maturity: MaturityLevel
    maturity_numeric: float
    confidence: ConfidenceLevel
    questions: List[QuestionResult]
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    summary_cell: str = ""  # <=50 words combined

class KeyTakeaway(BaseModel):
    title: str
    justification: str = Field(..., max_length=300)
    citations: List[CitationItem] = Field(default_factory=list)

class ReportData(BaseModel):
    run_id: str
    company_name: str
    company_domain: Optional[str] = None
    country: Optional[str] = None
    generated_at: datetime
    dimensions: List[DimensionResult]
    overall_maturity: MaturityLevel
    overall_maturity_numeric: float
    key_takeaways: List[KeyTakeaway] = Field(default_factory=list)
    bibliography: List[CitationItem] = Field(default_factory=list)
    validator_passed: bool = False
    sources_collected: int = 0
    sources_in_window: int = 0
