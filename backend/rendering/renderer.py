"""
Report renderer – generates HTML report and optionally PDF.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.config import settings
from backend.models import ReportData

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def render_html(
    report: ReportData,
    output_path: Path,
    maturity_visual_path: Optional[Path] = None,
    key_takeaways_path: Optional[Path] = None,
) -> Path:
    """Render the full HTML report and write it to output_path."""
    env = _get_jinja_env()
    template = env.get_template("report_template.html")

    # Build relative or absolute image references for the HTML
    visual_ref = None
    takeaways_ref = None

    if maturity_visual_path and maturity_visual_path.exists():
        visual_ref = maturity_visual_path.name  # relative if same dir
    if key_takeaways_path and key_takeaways_path.exists():
        takeaways_ref = key_takeaways_path.name

    html_content = template.render(
        report=report,
        maturity_visual_path=visual_ref,
        key_takeaways_path=takeaways_ref,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding="utf-8")
    logger.info("HTML report written to %s", output_path)
    return output_path


def render_pdf(
    html_path: Path,
    output_path: Path,
) -> Optional[Path]:
    """
    Render a PDF from the HTML report using Playwright.
    Returns path if successful, None otherwise.
    """
    if not settings.USE_PLAYWRIGHT:
        logger.info("PDF rendering skipped: Playwright disabled")
        return None

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"file://{html_path.resolve()}", wait_until="networkidle")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            page.pdf(
                path=str(output_path),
                format="A3",
                print_background=True,
                margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"},
            )
            browser.close()

        logger.info("PDF report written to %s", output_path)
        return output_path
    except Exception as exc:
        logger.warning("PDF rendering failed: %s", exc)
        return None
