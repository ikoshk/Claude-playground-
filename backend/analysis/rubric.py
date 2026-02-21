"""
IT Maturity Assessment – Full Rubric Definition (Q1–Q15).

This module defines the complete, immutable rubric used for assessment.
It is the single source of truth for scoring criteria, mapped signals,
evidence requirements, and dimension/sub-dimension mappings.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional


# ──────────────────────────────────────────────────────────────────────────────
# Rubric data structure
# ──────────────────────────────────────────────────────────────────────────────

RUBRIC: List[Dict] = [
    # ── Dimension 1: IT Strategy & Governance ─────────────────────────────────
    {
        "question_id": "Q1",
        "dimension_id": "D1",
        "dimension_name": "IT Strategy & Governance",
        "sub_dimension": "Business Relationship",
        "question_text": (
            "To what extent is IT positioned and evidenced publicly as a strategic "
            "business partner rather than a support function?"
        ),
        "mapped_signals": [
            "CIO/CTO on executive committee",
            "IT in corporate strategy documents",
            "digital transformation linked to revenue",
            "board-level technology oversight",
            "statements tying IT to growth/innovation",
        ],
        "scoring_criteria": {
            "Initial": "IT described mainly as operational/support.",
            "In development": "IT mentioned in transformation context but limited executive integration.",
            "Industrialized": "Clear executive role + recurring strategic alignment messaging.",
            "State of the art": "IT embedded in corporate strategy with measurable business impact.",
        },
        "evidence_requirements": {
            "Initial": {"min_sources": 1, "source_types": []},
            "In development": {"min_sources": 1, "source_types": []},
            "Industrialized": {"min_sources": 2, "source_types": ["independent"], "note": ">=2 independent sources"},
            "State of the art": {
                "min_sources": 2,
                "source_types": ["primary", "independent"],
                "note": ">=1 primary source (annual report/investor deck) + >=1 independent confirmation",
            },
        },
        "search_queries": [
            "{company} CIO CTO executive committee strategy",
            "{company} digital transformation revenue impact annual report",
            "{company} board technology oversight IT strategy",
            "{company} IT strategic partner innovation growth",
        ],
    },
    {
        "question_id": "Q2",
        "dimension_id": "D1",
        "dimension_name": "IT Strategy & Governance",
        "sub_dimension": "Business Relationship",
        "question_text": (
            "How clearly are mandates between IT, Digital, Data, and Business defined and governed?"
        ),
        "mapped_signals": [
            "Data Office / CDO defined",
            "Digital vs IT structure clarified",
            "governance committees",
            "RACI references",
            "data governance boards",
        ],
        "scoring_criteria": {
            "Initial": "No clear structure publicly described.",
            "In development": "Roles exist but limited clarity on governance.",
            "Industrialized": "Formal governance bodies + defined accountability.",
            "State of the art": "Integrated governance model across IT/Data/Digital.",
        },
        "evidence_requirements": {
            "Initial": {"min_sources": 0, "source_types": []},
            "In development": {"min_sources": 1, "source_types": []},
            "Industrialized": {
                "min_sources": 2,
                "source_types": ["independent"],
                "note": ">=2 independent sources or 1 governance report",
            },
            "State of the art": {
                "min_sources": 2,
                "source_types": ["independent"],
                "note": ">=2 independent sources or 1 governance report",
            },
        },
        "search_queries": [
            "{company} Chief Data Officer CDO governance structure",
            "{company} digital IT governance committee RACI",
            "{company} data governance board accountability",
            "{company} IT Digital mandate organization",
        ],
    },
    {
        "question_id": "Q3",
        "dimension_id": "D1",
        "dimension_name": "IT Strategy & Governance",
        "sub_dimension": "Business Technology Roadmap",
        "question_text": (
            "Is there evidence of a formal IT/IS roadmap aligned with business strategy?"
        ),
        "mapped_signals": [
            "multi-year IT roadmap",
            "cloud migration roadmap",
            "ERP modernization plan",
            "AI roadmap",
            "strategic transformation program",
        ],
        "scoring_criteria": {
            "Initial": "No roadmap evidence.",
            "In development": "Isolated initiatives.",
            "Industrialized": "Multi-year structured roadmap aligned to strategy.",
            "State of the art": "Roadmap linked to measurable KPIs.",
        },
        "evidence_requirements": {
            "Initial": {"min_sources": 0, "source_types": []},
            "In development": {"min_sources": 1, "source_types": []},
            "Industrialized": {"min_sources": 1, "source_types": ["primary"], "note": ">=1 primary source"},
            "State of the art": {
                "min_sources": 2,
                "source_types": ["primary"],
                "note": ">=2 sources including annual/investor report",
            },
        },
        "search_queries": [
            "{company} IT roadmap multi-year technology strategy",
            "{company} cloud migration roadmap ERP modernization",
            "{company} AI roadmap digital transformation program",
            "{company} technology investment plan KPI",
        ],
    },
    {
        "question_id": "Q4",
        "dimension_id": "D1",
        "dimension_name": "IT Strategy & Governance",
        "sub_dimension": "Build/Run Balance",
        "question_text": (
            "Is there evidence of active management of build vs run cost balance?"
        ),
        "mapped_signals": [
            "IT cost allocation",
            "transformation CAPEX/OPEX breakdown",
            "efficiency programs",
            "IT spend transparency",
        ],
        "scoring_criteria": {
            "Initial": "No financial visibility.",
            "In development": "Efficiency mentioned.",
            "Industrialized": "Explicit budget alignment with transformation.",
            "State of the art": "Value-based portfolio optimization publicly referenced.",
        },
        "evidence_requirements": {
            "Initial": {"min_sources": 0, "source_types": []},
            "In development": {"min_sources": 1, "source_types": []},
            "Industrialized": {
                "min_sources": 2,
                "source_types": ["financial"],
                "note": ">=1 financial disclosure + >=1 supporting source",
            },
            "State of the art": {
                "min_sources": 2,
                "source_types": ["financial"],
                "note": ">=1 financial disclosure + >=1 supporting source",
            },
        },
        "search_queries": [
            "{company} IT budget CAPEX OPEX allocation annual report",
            "{company} IT cost efficiency transformation spend",
            "{company} technology investment financial breakdown",
            "{company} IT portfolio optimization value",
        ],
    },
    # ── Dimension 2: Architecture & Innovation ─────────────────────────────────
    {
        "question_id": "Q5",
        "dimension_id": "D2",
        "dimension_name": "Architecture & Innovation",
        "sub_dimension": "Enterprise Architecture",
        "question_text": (
            "Is there evidence of structured enterprise architecture and technical debt management?"
        ),
        "mapped_signals": [
            "Enterprise Architecture team",
            "target architecture",
            "application rationalization",
            "technical debt reduction",
            "ERP consolidation",
        ],
        "scoring_criteria": {
            "Initial": "Legacy modernization only reactive.",
            "In development": "Modernization initiatives without formal EA discipline.",
            "Industrialized": "Formal EA practice + modernization roadmap.",
            "State of the art": "Architecture-driven transformation with measurable simplification.",
        },
        "evidence_requirements": {
            "Initial": {"min_sources": 0, "source_types": []},
            "In development": {"min_sources": 1, "source_types": []},
            "Industrialized": {
                "min_sources": 2,
                "source_types": ["independent"],
                "note": ">=2 independent sources or 1 primary transformation report",
            },
            "State of the art": {
                "min_sources": 2,
                "source_types": ["independent"],
                "note": ">=2 independent sources or 1 primary transformation report",
            },
        },
        "search_queries": [
            "{company} enterprise architecture EA team target architecture",
            "{company} technical debt reduction application rationalization",
            "{company} ERP consolidation legacy modernization",
            "{company} application portfolio simplification",
        ],
    },
    {
        "question_id": "Q6",
        "dimension_id": "D2",
        "dimension_name": "Architecture & Innovation",
        "sub_dimension": "Innovation",
        "question_text": (
            "How mature is structured innovation, including AI and emerging technologies?"
        ),
        "mapped_signals": [
            "AI strategy",
            "GenAI use cases",
            "innovation labs",
            "R&D budget",
            "partnerships with tech firms",
        ],
        "scoring_criteria": {
            "Initial": "Experimental pilots only.",
            "In development": "Structured pilots in defined domains.",
            "Industrialized": "Scaled AI initiatives with governance.",
            "State of the art": "Enterprise-wide AI embedded in operations.",
        },
        "evidence_requirements": {
            "Initial": {"min_sources": 0, "source_types": []},
            "In development": {"min_sources": 1, "source_types": []},
            "Industrialized": {
                "min_sources": 2,
                "source_types": ["independent"],
                "note": ">=2 independent sources",
            },
            "State of the art": {
                "min_sources": 2,
                "source_types": ["primary", "industry"],
                "note": ">=1 primary + >=1 industry source",
            },
        },
        "search_queries": [
            "{company} AI strategy artificial intelligence GenAI use cases",
            "{company} innovation lab R&D emerging technology",
            "{company} technology partnerships Microsoft Google AWS AI",
            "{company} generative AI deployment scale operations",
        ],
    },
    {
        "question_id": "Q7",
        "dimension_id": "D2",
        "dimension_name": "Architecture & Innovation",
        "sub_dimension": "Data Management",
        "question_text": (
            "Is there evidence of formal data governance and advanced analytics strategy?"
        ),
        "mapped_signals": [
            "data governance framework",
            "Chief Data Officer",
            "data platform/cloud data lake",
            "ML/AI at scale",
            "data catalog",
        ],
        "scoring_criteria": {
            "Initial": "Fragmented data use.",
            "In development": "Data platform announced.",
            "Industrialized": "Governance + advanced analytics roadmap.",
            "State of the art": "Enterprise data strategy tied to competitive advantage.",
        },
        "evidence_requirements": {
            "Initial": {"min_sources": 0, "source_types": []},
            "In development": {"min_sources": 1, "source_types": []},
            "Industrialized": {
                "min_sources": 2,
                "source_types": ["independent"],
                "note": ">=2 independent sources or governance documentation",
            },
            "State of the art": {
                "min_sources": 2,
                "source_types": ["independent"],
                "note": ">=2 independent sources or governance documentation",
            },
        },
        "search_queries": [
            "{company} data governance framework Chief Data Officer",
            "{company} data lake data platform cloud analytics",
            "{company} machine learning AI at scale data catalog",
            "{company} data strategy competitive advantage",
        ],
    },
    # ── Dimension 3: IT Business Management ───────────────────────────────────
    {
        "question_id": "Q8",
        "dimension_id": "D3",
        "dimension_name": "IT Business Management",
        "sub_dimension": "Sourcing & Supplier Management",
        "question_text": (
            "How mature is the IT sourcing strategy and supplier governance?"
        ),
        "mapped_signals": [
            "multi-vendor strategy",
            "cloud partnerships",
            "outsourcing model",
            "strategic technology alliances",
        ],
        "scoring_criteria": {
            "Initial": "Tactical vendor management.",
            "In development": "Defined sourcing approach.",
            "Industrialized": "Strategic partnerships aligned with roadmap.",
            "State of the art": "Ecosystem orchestration model.",
        },
        "evidence_requirements": {
            "Initial": {"min_sources": 0, "source_types": []},
            "In development": {"min_sources": 1, "source_types": []},
            "Industrialized": {
                "min_sources": 2,
                "source_types": ["independent"],
                "note": ">=2 independent sources",
            },
            "State of the art": {
                "min_sources": 2,
                "source_types": ["independent"],
                "note": ">=2 independent sources",
            },
        },
        "search_queries": [
            "{company} IT sourcing strategy vendor management outsourcing",
            "{company} cloud partnership AWS Azure Google strategic alliance",
            "{company} technology supplier governance multi-vendor",
            "{company} IT ecosystem partner model",
        ],
    },
    {
        "question_id": "Q9",
        "dimension_id": "D3",
        "dimension_name": "IT Business Management",
        "sub_dimension": "Sustainable IT",
        "question_text": (
            "Is there evidence of measurable green IT and responsible digital initiatives?"
        ),
        "mapped_signals": [
            "green IT roadmap",
            "IT carbon footprint reporting",
            "sustainable cloud strategy",
            "digital sustainability metrics",
        ],
        "scoring_criteria": {
            "Initial": "No mention.",
            "In development": "Sustainability mentioned generally.",
            "Industrialized": "Defined IT sustainability initiatives.",
            "State of the art": "Measured IT carbon footprint with reduction targets.",
        },
        "evidence_requirements": {
            "Initial": {"min_sources": 0, "source_types": []},
            "In development": {"min_sources": 1, "source_types": []},
            "Industrialized": {
                "min_sources": 1,
                "source_types": ["esg"],
                "note": ">=1 ESG report or sustainability disclosure",
            },
            "State of the art": {
                "min_sources": 1,
                "source_types": ["esg"],
                "note": ">=1 ESG report or sustainability disclosure",
            },
        },
        "search_queries": [
            "{company} green IT sustainability carbon footprint digital",
            "{company} ESG report sustainable technology cloud",
            "{company} IT carbon reduction responsible digital",
            "{company} sustainable cloud strategy energy efficiency",
        ],
    },
    # ── Dimension 4: Product Delivery ──────────────────────────────────────────
    {
        "question_id": "Q10",
        "dimension_id": "D4",
        "dimension_name": "Product Delivery",
        "sub_dimension": "Infrastructure Management",
        "question_text": (
            "How mature is cloud adoption and infrastructure scalability?"
        ),
        "mapped_signals": [
            "multi-cloud strategy",
            "hybrid cloud",
            "platform engineering",
            "infrastructure as code",
            "hyperscaler partnerships",
        ],
        "scoring_criteria": {
            "Initial": "On-prem dominant.",
            "In development": "Partial cloud migration.",
            "Industrialized": "Structured hybrid/multi-cloud.",
            "State of the art": "Cloud-native platform at scale.",
        },
        "evidence_requirements": {
            "Initial": {"min_sources": 0, "source_types": []},
            "In development": {"min_sources": 1, "source_types": []},
            "Industrialized": {
                "min_sources": 2,
                "source_types": ["independent"],
                "note": ">=2 independent sources",
            },
            "State of the art": {
                "min_sources": 2,
                "source_types": ["independent"],
                "note": ">=2 independent sources",
            },
        },
        "search_queries": [
            "{company} cloud migration multi-cloud hybrid cloud strategy",
            "{company} AWS Azure Google Cloud partnership hyperscaler",
            "{company} infrastructure as code platform engineering",
            "{company} cloud-native infrastructure scalability",
        ],
    },
    {
        "question_id": "Q11",
        "dimension_id": "D4",
        "dimension_name": "Product Delivery",
        "sub_dimension": "IT Service Management",
        "question_text": (
            "Is there evidence of structured ITSM processes and tooling?"
        ),
        "mapped_signals": [
            "ServiceNow / ITSM tools",
            "ITIL",
            "SLA metrics",
            "continuous improvement",
        ],
        "scoring_criteria": {
            "Initial": "Reactive IT support.",
            "In development": "Tool adoption.",
            "Industrialized": "Mature ITIL-based processes.",
            "State of the art": "Data-driven IT operations optimization.",
        },
        "evidence_requirements": {
            "Initial": {"min_sources": 0, "source_types": []},
            "In development": {"min_sources": 1, "source_types": []},
            "Industrialized": {
                "min_sources": 2,
                "source_types": ["tool", "operational"],
                "note": ">=1 tool confirmation + >=1 operational reference",
            },
            "State of the art": {
                "min_sources": 2,
                "source_types": ["tool", "operational"],
                "note": ">=1 tool confirmation + >=1 operational reference",
            },
        },
        "search_queries": [
            "{company} ServiceNow ITSM ITIL service management",
            "{company} SLA metrics IT operations continuous improvement",
            "{company} IT service desk incident management",
            "{company} AIOps IT operations optimization",
        ],
    },
    # ── Dimension 5: Security & Risk ────────────────────────────────────────────
    {
        "question_id": "Q12",
        "dimension_id": "D5",
        "dimension_name": "Security & Risk",
        "sub_dimension": "Security Management",
        "question_text": (
            "Is cybersecurity governed strategically with detection and response capabilities?"
        ),
        "mapped_signals": [
            "SOC",
            "Zero Trust",
            "incident response",
            "cyber resilience",
            "CISO presence",
        ],
        "scoring_criteria": {
            "Initial": "Basic controls only.",
            "In development": "Defined cyber strategy.",
            "Industrialized": "Active SOC + formal governance.",
            "State of the art": "Advanced detection + Zero Trust + board oversight.",
        },
        "evidence_requirements": {
            "Initial": {"min_sources": 0, "source_types": []},
            "In development": {"min_sources": 1, "source_types": []},
            "Industrialized": {
                "min_sources": 2,
                "source_types": ["independent"],
                "note": ">=2 independent sources",
            },
            "State of the art": {
                "min_sources": 2,
                "source_types": ["primary", "cyber"],
                "note": ">=1 primary report + >=1 cyber-specific source",
            },
        },
        "search_queries": [
            "{company} CISO cybersecurity SOC security operations center",
            "{company} Zero Trust incident response cyber resilience",
            "{company} cybersecurity strategy board governance",
            "{company} cyber threat detection security posture",
        ],
    },
    {
        "question_id": "Q13",
        "dimension_id": "D5",
        "dimension_name": "Security & Risk",
        "sub_dimension": "Risk, Continuity & Compliance",
        "question_text": (
            "Is there formal DRP/BCP and enterprise IT risk governance?"
        ),
        "mapped_signals": [
            "Disaster Recovery Plan",
            "Business Continuity Plan",
            "regulatory compliance (e.g., NIS2, DORA)",
            "risk committees",
        ],
        "scoring_criteria": {
            "Initial": "No visible structure.",
            "In development": "Policy-level statements.",
            "Industrialized": "Structured DRP/BCP framework.",
            "State of the art": "Tested resilience programs + regulatory alignment.",
        },
        "evidence_requirements": {
            "Initial": {"min_sources": 0, "source_types": []},
            "In development": {"min_sources": 1, "source_types": []},
            "Industrialized": {
                "min_sources": 2,
                "source_types": ["governance"],
                "note": ">=1 governance disclosure + >=1 supporting source",
            },
            "State of the art": {
                "min_sources": 2,
                "source_types": ["governance"],
                "note": ">=1 governance disclosure + >=1 supporting source",
            },
        },
        "search_queries": [
            "{company} disaster recovery business continuity BCP DRP",
            "{company} NIS2 DORA regulatory compliance IT risk",
            "{company} IT risk committee governance resilience",
            "{company} operational resilience regulatory framework",
        ],
    },
    # ── Dimension 6: Methods & Tools ───────────────────────────────────────────
    {
        "question_id": "Q14",
        "dimension_id": "D6",
        "dimension_name": "Methods & Tools",
        "sub_dimension": "Agile",
        "question_text": (
            "Is agile institutionalized beyond isolated teams?"
        ),
        "mapped_signals": [
            "SAFe",
            "Agile Office",
            "product-centric organization",
            "Scrum adoption",
            "end-user feedback loops",
        ],
        "scoring_criteria": {
            "Initial": "Isolated agile teams.",
            "In development": "Broader adoption.",
            "Industrialized": "Scaled agile framework.",
            "State of the art": "Enterprise product operating model.",
        },
        "evidence_requirements": {
            "Initial": {"min_sources": 0, "source_types": []},
            "In development": {"min_sources": 1, "source_types": []},
            "Industrialized": {
                "min_sources": 2,
                "source_types": ["independent"],
                "note": ">=2 independent sources",
            },
            "State of the art": {
                "min_sources": 2,
                "source_types": ["independent"],
                "note": ">=2 independent sources",
            },
        },
        "search_queries": [
            "{company} agile at scale SAFe Agile Office product-centric",
            "{company} Scrum agile transformation organization",
            "{company} product operating model agile squads",
            "{company} end-user feedback agile delivery",
        ],
    },
    {
        "question_id": "Q15",
        "dimension_id": "D6",
        "dimension_name": "Methods & Tools",
        "sub_dimension": "DevOps",
        "question_text": (
            "Is DevOps embedded with automation and CI/CD at scale?"
        ),
        "mapped_signals": [
            "CI/CD pipelines",
            "SRE roles",
            "Infrastructure as code",
            "DevSecOps",
            "platform engineering",
        ],
        "scoring_criteria": {
            "Initial": "Manual deployments.",
            "In development": "CI/CD in limited scope.",
            "Industrialized": "Enterprise-wide DevOps practice.",
            "State of the art": "Fully automated pipelines + integrated DevSecOps.",
        },
        "evidence_requirements": {
            "Initial": {"min_sources": 0, "source_types": []},
            "In development": {"min_sources": 1, "source_types": []},
            "Industrialized": {
                "min_sources": 2,
                "source_types": ["independent"],
                "note": ">=2 independent sources or 1 primary tech disclosure",
            },
            "State of the art": {
                "min_sources": 2,
                "source_types": ["independent"],
                "note": ">=2 independent sources or 1 primary tech disclosure",
            },
        },
        "search_queries": [
            "{company} DevOps CI/CD pipelines continuous deployment",
            "{company} SRE site reliability engineering platform engineering",
            "{company} DevSecOps infrastructure as code automation",
            "{company} deployment frequency release automation",
        ],
    },
]

# ──────────────────────────────────────────────────────────────────────────────
# Dimension layout
# ──────────────────────────────────────────────────────────────────────────────

DIMENSION_QUESTION_MAP: Dict[str, List[str]] = {
    "D1": ["Q1", "Q2", "Q3", "Q4"],
    "D2": ["Q5", "Q6", "Q7"],
    "D3": ["Q8", "Q9"],
    "D4": ["Q10", "Q11"],
    "D5": ["Q12", "Q13"],
    "D6": ["Q14", "Q15"],
}

DIMENSION_NAMES: Dict[str, str] = {
    "D1": "IT Strategy & Governance",
    "D2": "Architecture & Innovation",
    "D3": "IT Business Management",
    "D4": "Product Delivery",
    "D5": "Security & Risk",
    "D6": "Methods & Tools",
}

# Build lookup index
RUBRIC_BY_ID: Dict[str, Dict] = {q["question_id"]: q for q in RUBRIC}


def get_question(question_id: str) -> Dict:
    """Return rubric entry by question ID."""
    if question_id not in RUBRIC_BY_ID:
        raise KeyError(f"Unknown question_id: {question_id}")
    return RUBRIC_BY_ID[question_id]


def get_dimension_questions(dimension_id: str) -> List[Dict]:
    """Return all rubric entries for a given dimension."""
    return [q for q in RUBRIC if q["dimension_id"] == dimension_id]


def rubric_to_json() -> str:
    """Export the rubric to a JSON string (for external use)."""
    return json.dumps(RUBRIC, indent=2)


def get_all_search_queries(company_name: str, company_domain: Optional[str] = None) -> List[Dict]:
    """
    Return all search queries across all questions, formatted for the given company.
    Each item: {"question_id": ..., "query": ...}
    """
    results = []
    for question in RUBRIC:
        for template in question["search_queries"]:
            query = template.replace("{company}", company_name)
            results.append({
                "question_id": question["question_id"],
                "query": query,
                "dimension_id": question["dimension_id"],
            })
    return results
