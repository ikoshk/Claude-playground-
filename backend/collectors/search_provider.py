"""
Search provider implementations:
  - StubSearchProvider      – deterministic mock, used in demo mode
  - TavilySearchProvider    – real Tavily API
  - SerpAPISearchProvider   – real SerpAPI
  - BingSearchProvider      – real Bing Web Search API

Factory function: get_search_provider()
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import List, Optional
from urllib.parse import urlparse

import httpx

from backend.collectors.base import SearchProvider, SearchResult
from backend.config import settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ──────────────────────────────────────────────────────────────────────────────

def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def _parse_date(raw: Optional[str]) -> Optional[str]:
    """Normalize a date string to YYYY-MM-DD where possible."""
    if not raw:
        return None
    # Already YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    # YYYY-MM
    m = re.match(r"^(\d{4})-(\d{2})$", raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}-01"
    # YYYY
    m = re.match(r"^(\d{4})$", raw)
    if m:
        return f"{m.group(1)}-01-01"
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Stub provider (demo mode)
# ──────────────────────────────────────────────────────────────────────────────

_STUB_TEMPLATES = [
    {
        "url": "https://{domain}/investor-relations/annual-report-2024",
        "title": "{company} Annual Report 2024 – Technology Strategy",
        "snippet": (
            "{company} continued to invest in its digital transformation roadmap, "
            "with the CIO presenting technology strategy at the board level. Cloud "
            "migration to AWS and Azure advanced to 65% of workloads. AI initiatives "
            "including GenAI use cases were scaled across business units."
        ),
        "published_date": "2024-03-15",
        "is_primary": True,
        "source_type": "annual_report",
    },
    {
        "url": "https://{domain}/press/2024/digital-transformation-milestone",
        "title": "{company} Achieves Key Digital Transformation Milestone",
        "snippet": (
            "{company} announced completion of Phase 1 of its multi-year IT roadmap, "
            "reducing technical debt by 30% through ERP consolidation and application "
            "rationalization. The Chief Data Officer confirmed governance framework rollout."
        ),
        "published_date": "2024-06-01",
        "is_primary": True,
        "source_type": "press_release",
    },
    {
        "url": "https://techcrunch.com/2024/05/{company_slug}-cloud-strategy",
        "title": "{company} Accelerates Multi-Cloud Strategy with AWS Partnership",
        "snippet": (
            "{company} deepened its hyperscaler partnership with AWS, deploying "
            "infrastructure-as-code practices across its platform engineering team. "
            "The company also announced a Zero Trust security architecture rollout "
            "overseen by its newly appointed CISO."
        ),
        "published_date": "2024-05-10",
        "is_primary": False,
        "source_type": "news",
    },
    {
        "url": "https://aws.amazon.com/solutions/case-studies/{company_slug}",
        "title": "{company} Case Study – Cloud Migration at Scale",
        "snippet": (
            "{company} migrated 70% of its infrastructure to AWS, leveraging hybrid "
            "cloud architecture. Platform engineering teams adopted DevOps practices "
            "including CI/CD pipelines and SRE roles, reducing deployment time by 60%."
        ),
        "published_date": "2023-11-20",
        "is_primary": False,
        "source_type": "vendor_case_study",
    },
    {
        "url": "https://{domain}/esg/sustainability-report-2024",
        "title": "{company} ESG Report 2024 – Sustainable IT",
        "snippet": (
            "{company} reported a 20% reduction in IT carbon footprint in 2023 through "
            "sustainable cloud strategy and data center consolidation. Measurable digital "
            "sustainability metrics are now published annually."
        ),
        "published_date": "2024-04-30",
        "is_primary": True,
        "source_type": "esg_report",
    },
    {
        "url": "https://www.gartner.com/research/{company_slug}-it-maturity",
        "title": "Gartner Peer Insights: {company} IT Governance",
        "snippet": (
            "Reviewers note {company} has implemented SAFe at scale, with an Agile "
            "Office coordinating multiple product teams. ServiceNow ITSM deployment "
            "supports ITIL-based incident management and continuous improvement."
        ),
        "published_date": "2024-02-14",
        "is_primary": False,
        "source_type": "analyst_report",
    },
    {
        "url": "https://linkedin.com/jobs/{company_slug}-sre-devops",
        "title": "{company} – Site Reliability Engineer / DevSecOps Lead (Job Posting)",
        "snippet": (
            "Join {company}'s platform engineering team. We practice DevSecOps with "
            "integrated security in CI/CD pipelines. Seeking SRE leads for our "
            "cloud-native infrastructure. Infrastructure as code is standard practice."
        ),
        "published_date": "2024-08-01",
        "is_primary": False,
        "source_type": "job_posting",
    },
    {
        "url": "https://{domain}/newsroom/2023/cybersecurity-soc-launch",
        "title": "{company} Launches 24/7 Security Operations Centre",
        "snippet": (
            "{company} established a dedicated Security Operations Centre (SOC) with "
            "advanced threat detection capabilities. The CISO leads a cyber resilience "
            "program aligned with NIS2 regulations, including formal DRP/BCP frameworks "
            "tested quarterly."
        ),
        "published_date": "2023-09-05",
        "is_primary": True,
        "source_type": "press_release",
    },
]


class StubSearchProvider(SearchProvider):
    """Returns deterministic mock results for demo/testing mode."""

    @property
    def name(self) -> str:
        return "Stub (Demo Mode)"

    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        company = query.split()[0] if query else "Company"
        domain_guess = f"{company.lower().replace(' ', '')}.com"
        slug = company.lower().replace(" ", "-")

        results = []
        for tpl in _STUB_TEMPLATES:
            url = tpl["url"].format(company=company, domain=domain_guess, company_slug=slug)
            title = tpl["title"].format(company=company, domain=domain_guess, company_slug=slug)
            snippet = tpl["snippet"].format(company=company, domain=domain_guess, company_slug=slug)
            results.append(
                SearchResult(
                    url=url,
                    title=title,
                    snippet=snippet,
                    published_date=tpl["published_date"],
                    source_domain=_domain(url),
                    query=query,
                )
            )
        return results[:num_results]


# ──────────────────────────────────────────────────────────────────────────────
# Tavily provider
# ──────────────────────────────────────────────────────────────────────────────

class TavilySearchProvider(SearchProvider):
    """Tavily Search API – best for research/news."""

    BASE_URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str):
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "Tavily"

    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        payload = {
            "api_key": self._api_key,
            "query": query,
            "max_results": num_results,
            "search_depth": "advanced",
            "include_answer": False,
            "include_raw_content": False,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(self.BASE_URL, json=payload)
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.warning("Tavily search failed for %r: %s", query, exc)
                return []

        results = []
        for item in data.get("results", []):
            results.append(
                SearchResult(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    snippet=item.get("content", ""),
                    published_date=_parse_date(item.get("published_date")),
                    source_domain=_domain(item.get("url", "")),
                    query=query,
                )
            )
        return results


# ──────────────────────────────────────────────────────────────────────────────
# SerpAPI provider
# ──────────────────────────────────────────────────────────────────────────────

class SerpAPISearchProvider(SearchProvider):
    BASE_URL = "https://serpapi.com/search"

    def __init__(self, api_key: str):
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "SerpAPI"

    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        params = {
            "engine": "google",
            "q": query,
            "api_key": self._api_key,
            "num": num_results,
            "hl": "en",
            "gl": "us",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.warning("SerpAPI search failed for %r: %s", query, exc)
                return []

        results = []
        for item in data.get("organic_results", []):
            pub_date = None
            if "date" in item:
                pub_date = _parse_date(item["date"])
            results.append(
                SearchResult(
                    url=item.get("link", ""),
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                    published_date=pub_date,
                    source_domain=_domain(item.get("link", "")),
                    query=query,
                )
            )
        return results


# ──────────────────────────────────────────────────────────────────────────────
# Bing provider
# ──────────────────────────────────────────────────────────────────────────────

class BingSearchProvider(SearchProvider):
    BASE_URL = "https://api.bing.microsoft.com/v7.0/search"

    def __init__(self, api_key: str):
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "Bing"

    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        headers = {"Ocp-Apim-Subscription-Key": self._api_key}
        params = {"q": query, "count": num_results, "mkt": "en-US"}
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(self.BASE_URL, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.warning("Bing search failed for %r: %s", query, exc)
                return []

        results = []
        for item in data.get("webPages", {}).get("value", []):
            pub_date = _parse_date(item.get("datePublished") or item.get("dateLastCrawled"))
            results.append(
                SearchResult(
                    url=item.get("url", ""),
                    title=item.get("name", ""),
                    snippet=item.get("snippet", ""),
                    published_date=pub_date,
                    source_domain=_domain(item.get("url", "")),
                    query=query,
                )
            )
        return results


# ──────────────────────────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────────────────────────

def get_search_provider() -> SearchProvider:
    """Return the configured search provider based on env vars."""
    provider = settings.SEARCH_PROVIDER.lower()
    if provider == "tavily" and settings.TAVILY_API_KEY:
        logger.info("Using Tavily search provider")
        return TavilySearchProvider(settings.TAVILY_API_KEY)
    elif provider == "serpapi" and settings.SERPAPI_KEY:
        logger.info("Using SerpAPI search provider")
        return SerpAPISearchProvider(settings.SERPAPI_KEY)
    elif provider == "bing" and settings.BING_API_KEY:
        logger.info("Using Bing search provider")
        return BingSearchProvider(settings.BING_API_KEY)
    else:
        logger.info("Using Stub search provider (demo mode)")
        return StubSearchProvider()
