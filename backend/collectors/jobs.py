"""
Job postings collector – infers technology stack and operating model
from publicly accessible job listings (LinkedIn, company careers pages).
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional
from urllib.parse import quote_plus

from backend.collectors.base import SearchResult
from backend.collectors.crawler import fetch_page

logger = logging.getLogger(__name__)


# Tech signal keywords to look for in job postings
TECH_SIGNALS = [
    "CI/CD", "DevOps", "DevSecOps", "SRE", "Site Reliability",
    "Infrastructure as code", "Terraform", "Kubernetes", "Docker",
    "ServiceNow", "ITIL", "ITSM",
    "Agile", "SAFe", "Scrum",
    "Zero Trust", "SOC", "SIEM",
    "AWS", "Azure", "GCP", "multi-cloud",
    "Data Governance", "Data Lake", "Databricks", "Snowflake",
    "AI", "Machine Learning", "GenAI", "LLM",
    "Enterprise Architecture", "TOGAF",
    "ERP", "SAP", "Oracle",
    "Platform Engineering",
]


def extract_signals_from_text(text: str) -> List[str]:
    """Find tech signals in free text."""
    found = []
    lower = text.lower()
    for sig in TECH_SIGNALS:
        if sig.lower() in lower:
            found.append(sig)
    return list(set(found))


async def collect_job_signals(
    company_name: str, company_domain: Optional[str] = None
) -> List[dict]:
    """
    Fetch a sample of job postings and extract tech signals.
    Returns list of signal dicts.
    """
    # Build search URLs for job postings
    encoded = quote_plus(company_name)
    urls_to_try = [
        f"https://www.linkedin.com/jobs/search/?keywords={encoded}+technology",
    ]
    if company_domain:
        domain = company_domain.replace("www.", "")
        urls_to_try.append(f"https://{domain}/careers")
        urls_to_try.append(f"https://{domain}/jobs")

    all_signals = []
    for url in urls_to_try[:2]:
        try:
            page = await fetch_page(url)
            if page and page.get("text"):
                signals = extract_signals_from_text(page["text"])
                if signals:
                    all_signals.append(
                        {
                            "url": url,
                            "signals": signals,
                            "published_date": None,
                            "source_type": "job_posting",
                        }
                    )
        except Exception as exc:
            logger.debug("Job posting fetch failed for %s: %s", url, exc)

    return all_signals
