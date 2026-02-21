"""
Web crawler – fetches and extracts clean text from URLs.
Tries Playwright (headless) first, falls back to requests + BeautifulSoup.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from backend.config import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Date extraction helpers
# ──────────────────────────────────────────────────────────────────────────────

_DATE_PATTERNS = [
    # ISO: 2024-03-15
    re.compile(r"(\d{4}-\d{2}-\d{2})"),
    # Written: March 15, 2024 / 15 March 2024
    re.compile(
        r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})",
        re.IGNORECASE,
    ),
    # URL pattern: /2024/03/ or /2024-03-
    re.compile(r"/(\d{4})/(\d{2})/"),
]

_MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}


def _normalize_date(raw: str) -> Optional[str]:
    """Try to normalize a raw date string to YYYY-MM-DD."""
    raw = raw.strip()
    # Already ISO
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    # YYYY/MM
    m = re.match(r"^(\d{4})/(\d{2})$", raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}-01"
    # "Month DD, YYYY" or "Month YYYY"
    for pat in [
        r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})$",
        r"^(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})$",
    ]:
        m = re.match(pat, raw, re.IGNORECASE)
        if m:
            groups = m.groups()
            # figure out month
            for g in groups:
                if g.lower() in _MONTH_MAP:
                    month = _MONTH_MAP[g.lower()]
                    year = groups[-1]
                    # day
                    day = "01"
                    for g2 in groups:
                        if g2.isdigit() and len(g2) <= 2:
                            day = g2.zfill(2)
                    return f"{year}-{month}-{day}"
    return None


def extract_date_from_url(url: str) -> Optional[str]:
    """Try to extract a publish date from URL patterns like /2024/03/."""
    m = re.search(r"/(\d{4})/(\d{2})/", url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-01"
    m = re.search(r"/(\d{4})-(\d{2})-(\d{2})/", url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def extract_date_from_html(soup: BeautifulSoup, url: str) -> Tuple[Optional[str], str]:
    """
    Extract published date from HTML meta tags and schema.org.
    Returns (date_str, confidence) where confidence is 'exact', 'approximate', or 'unknown'.
    """
    # 1. Meta tags
    for attr_val in [
        ("name", "article:published_time"),
        ("property", "article:published_time"),
        ("name", "pubdate"),
        ("name", "date"),
        ("name", "DC.date"),
        ("itemprop", "datePublished"),
    ]:
        tag = soup.find("meta", attrs={attr_val[0]: attr_val[1]})
        if tag and tag.get("content"):
            d = _normalize_date(tag["content"][:10])
            if d:
                return d, "exact"

    # 2. time element
    time_tag = soup.find("time", attrs={"datetime": True})
    if time_tag:
        d = _normalize_date(time_tag["datetime"][:10])
        if d:
            return d, "exact"

    # 3. JSON-LD schema.org
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            import json
            data = json.loads(script.string or "")
            for key in ["datePublished", "dateModified", "uploadDate"]:
                if key in data:
                    d = _normalize_date(str(data[key])[:10])
                    if d:
                        return d, "exact"
        except Exception:
            pass

    # 4. URL pattern
    d = extract_date_from_url(url)
    if d:
        return d, "approximate"

    # 5. Text scan (first date-like pattern in body)
    body_text = soup.get_text(" ", strip=True)[:2000]
    for pat in _DATE_PATTERNS[:-1]:
        m = pat.search(body_text)
        if m:
            raw = m.group(0)
            d = _normalize_date(raw)
            if d:
                return d, "approximate"

    return None, "unknown"


def is_in_window(date_str: Optional[str]) -> bool:
    """Return True if date is within EVIDENCE_WINDOW_START – EVIDENCE_WINDOW_END."""
    if not date_str:
        return False
    try:
        year = int(date_str[:4])
        return settings.EVIDENCE_WINDOW_START <= year <= settings.EVIDENCE_WINDOW_END
    except Exception:
        return False


def is_primary_source(url: str, company_domain: Optional[str] = None) -> bool:
    """
    Heuristic: is this URL a primary source (company-owned or official filing)?
    """
    domain = urlparse(url).netloc.lower().replace("www.", "")
    # Company domain matches
    if company_domain:
        cd = company_domain.lower().replace("www.", "")
        if domain == cd or domain.endswith("." + cd):
            return True
    # Known filings / IR domains
    primary_indicators = [
        "sec.gov", "sedar.com", "companieshouse.gov.uk",
        "investor.relations", "ir.", "investors.",
        "annualreport", "annual-report",
        "esg-report", "sustainability-report",
        "amf-france.org",
    ]
    return any(ind in url.lower() for ind in primary_indicators)


def compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def clean_text(soup: BeautifulSoup) -> str:
    """Extract clean readable text from BeautifulSoup object."""
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    # Collapse whitespace
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines)[: settings.MAX_TEXT_CHARS_PER_DOC]


# ──────────────────────────────────────────────────────────────────────────────
# Fetch implementations
# ──────────────────────────────────────────────────────────────────────────────

async def fetch_with_httpx(url: str) -> Tuple[Optional[str], Optional[BeautifulSoup]]:
    """Lightweight fetch using httpx."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; ITMaturityBot/1.0; "
            "+https://github.com/itmaturity-assessment)"
        )
    }
    try:
        async with httpx.AsyncClient(
            timeout=settings.FETCH_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers=headers,
        ) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None, None
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")
            return html, soup
    except Exception as exc:
        logger.debug("httpx fetch failed for %s: %s", url, exc)
        return None, None


async def fetch_with_playwright(url: str) -> Tuple[Optional[str], Optional[BeautifulSoup]]:
    """Headless browser fetch using Playwright (async)."""
    if not settings.USE_PLAYWRIGHT:
        return None, None
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=settings.PLAYWRIGHT_HEADLESS)
            try:
                page = await browser.new_page()
                await page.goto(url, timeout=settings.FETCH_TIMEOUT_SECONDS * 1000)
                await page.wait_for_load_state("domcontentloaded")
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                return html, soup
            finally:
                await browser.close()
    except Exception as exc:
        logger.debug("Playwright fetch failed for %s: %s", url, exc)
        return None, None


async def fetch_page(url: str) -> Optional[dict]:
    """
    Fetch a page and return structured data.
    Returns dict with: url, title, text, published_date, date_confidence,
                       content_hash, source_type
    or None if fetch fails.
    """
    # Try httpx first (faster), fall back to Playwright for JS-heavy pages
    html, soup = await fetch_with_httpx(url)
    if not html or not soup:
        html, soup = await fetch_with_playwright(url)
    if not html or not soup:
        return None

    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)

    text = clean_text(soup)
    published_date, date_confidence = extract_date_from_html(soup, url)
    content_hash = compute_content_hash(text)

    return {
        "url": url,
        "title": title,
        "text": text,
        "published_date": published_date,
        "date_confidence": date_confidence,
        "content_hash": content_hash,
        "source_type": "html",
    }
