"""
PDF text extraction – tries pdfplumber first, falls back to pypdf.
"""
from __future__ import annotations

import io
import logging
import re
from typing import Optional, Tuple
from datetime import datetime

import httpx

from backend.config import settings
from backend.collectors.crawler import compute_content_hash

logger = logging.getLogger(__name__)


def extract_pdf_text(pdf_bytes: bytes) -> Tuple[str, Optional[str]]:
    """
    Extract text and publish date from PDF bytes.
    Returns (text, published_date_str).
    """
    text = ""
    pub_date = None

    # Try pdfplumber
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            # Extract date from metadata
            meta = pdf.metadata or {}
            for key in ["CreationDate", "ModDate"]:
                raw = meta.get(key, "")
                if raw:
                    pub_date = _parse_pdf_date(raw)
                    if pub_date:
                        break

            pages_text = []
            for page in pdf.pages[: 100]:  # cap at 100 pages
                pg_text = page.extract_text() or ""
                pages_text.append(pg_text)
            text = "\n".join(pages_text)[: settings.MAX_TEXT_CHARS_PER_DOC]

        if text.strip():
            return text, pub_date
    except Exception as exc:
        logger.debug("pdfplumber failed: %s", exc)

    # Fallback to pypdf
    try:
        import pypdf

        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        meta = reader.metadata or {}
        for key in ["/CreationDate", "/ModDate"]:
            raw = meta.get(key, "")
            if raw:
                pub_date = _parse_pdf_date(str(raw))
                if pub_date:
                    break

        pages_text = []
        for page in reader.pages[:100]:
            pages_text.append(page.extract_text() or "")
        text = "\n".join(pages_text)[: settings.MAX_TEXT_CHARS_PER_DOC]
    except Exception as exc:
        logger.debug("pypdf failed: %s", exc)

    return text, pub_date


def _parse_pdf_date(raw: str) -> Optional[str]:
    """Parse PDF date format D:YYYYMMDDHHmmSS to YYYY-MM-DD."""
    # PDF format: D:20240315120000+00'00'
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})", raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    # ISO format already
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


async def fetch_pdf(url: str) -> Optional[dict]:
    """
    Download and extract a PDF from URL.
    Returns structured dict or None.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; ITMaturityBot/1.0)"
        )
    }
    try:
        async with httpx.AsyncClient(
            timeout=60,
            follow_redirects=True,
            headers=headers,
        ) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None
            content_type = resp.headers.get("content-type", "")
            if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
                return None
            pdf_bytes = resp.content
    except Exception as exc:
        logger.debug("PDF download failed for %s: %s", url, exc)
        return None

    text, pub_date = extract_pdf_text(pdf_bytes)
    if not text.strip():
        return None

    return {
        "url": url,
        "title": url.split("/")[-1],
        "text": text,
        "published_date": pub_date,
        "date_confidence": "exact" if pub_date else "unknown",
        "content_hash": compute_content_hash(text),
        "source_type": "pdf",
    }
