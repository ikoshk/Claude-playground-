"""
Image generation using Matplotlib.

Generates:
  - maturity_visual.png  : Six labeled blocks showing dimension maturity scores
  - key_takeaways.png    : "Key Takeaways" block with up to 5 action items
"""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import List

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

from backend.models import DimensionResult, KeyTakeaway, MaturityLevel

# Colour palette aligned to maturity levels
MATURITY_COLORS = {
    MaturityLevel.INITIAL: "#E74C3C",           # Red
    MaturityLevel.IN_DEVELOPMENT: "#F39C12",    # Orange
    MaturityLevel.INDUSTRIALIZED: "#2980B9",    # Blue
    MaturityLevel.STATE_OF_THE_ART: "#27AE60",  # Green
}

BACKGROUND_COLOR = "#1A1A2E"
CARD_EDGE_COLOR = "#16213E"
TEXT_COLOR = "#EAEAEA"
ACCENT_COLOR = "#0F3460"
HEADER_COLOR = "#E94560"


def generate_maturity_visual(
    dimensions: List[DimensionResult],
    output_path: Path,
    company_name: str,
) -> Path:
    """
    Generate maturity_visual.png:
    Six labeled blocks showing dimension name and maturity score text.
    """
    fig = plt.figure(figsize=(14, 8), facecolor=BACKGROUND_COLOR)
    fig.suptitle(
        f"IT Maturity Assessment – {company_name}",
        fontsize=16,
        fontweight="bold",
        color=TEXT_COLOR,
        y=0.97,
    )

    n_dims = len(dimensions)
    cols = 3
    rows = (n_dims + cols - 1) // cols

    gs = GridSpec(rows, cols, figure=fig, hspace=0.4, wspace=0.35)
    gs.update(left=0.05, right=0.95, top=0.88, bottom=0.08)

    for idx, dim in enumerate(dimensions):
        row = idx // cols
        col = idx % cols
        ax = fig.add_subplot(gs[row, col])
        ax.set_facecolor(ACCENT_COLOR)

        maturity_color = MATURITY_COLORS.get(dim.maturity, "#7F8C8D")
        numeric = dim.maturity_numeric

        # Draw coloured border rectangle
        rect = mpatches.FancyBboxPatch(
            (0, 0), 1, 1,
            boxstyle="round,pad=0.02",
            linewidth=3,
            edgecolor=maturity_color,
            facecolor=ACCENT_COLOR,
            transform=ax.transAxes,
            clip_on=False,
        )
        ax.add_patch(rect)

        # Dimension name
        dim_name_wrapped = "\n".join(textwrap.wrap(dim.dimension_name, width=20))
        ax.text(
            0.5, 0.78,
            dim_name_wrapped,
            ha="center", va="center",
            fontsize=9, fontweight="bold",
            color=TEXT_COLOR,
            transform=ax.transAxes,
        )

        # Maturity level text (large)
        maturity_wrapped = "\n".join(textwrap.wrap(dim.maturity.value, width=14))
        ax.text(
            0.5, 0.45,
            maturity_wrapped,
            ha="center", va="center",
            fontsize=11, fontweight="bold",
            color=maturity_color,
            transform=ax.transAxes,
        )

        # Numeric score
        ax.text(
            0.5, 0.18,
            f"{numeric:.1f} / 4.0",
            ha="center", va="center",
            fontsize=8,
            color=TEXT_COLOR,
            transform=ax.transAxes,
            alpha=0.8,
        )

        ax.axis("off")

    # Legend
    legend_elements = [
        mpatches.Patch(color=MATURITY_COLORS[m], label=m.value)
        for m in MaturityLevel
    ]
    fig.legend(
        handles=legend_elements,
        loc="lower center",
        ncol=4,
        fontsize=8,
        framealpha=0.3,
        facecolor=ACCENT_COLOR,
        edgecolor=TEXT_COLOR,
        labelcolor=TEXT_COLOR,
        bbox_to_anchor=(0.5, 0.0),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(output_path), dpi=150, bbox_inches="tight", facecolor=BACKGROUND_COLOR)
    plt.close(fig)
    return output_path


def generate_key_takeaways_visual(
    takeaways: List[KeyTakeaway],
    output_path: Path,
    company_name: str,
) -> Path:
    """
    Generate key_takeaways.png:
    Title "Key Takeaways" + up to 5 action items.
    """
    n = min(len(takeaways), 5)
    fig_height = 2.5 + n * 1.4

    fig, ax = plt.subplots(figsize=(12, fig_height), facecolor=BACKGROUND_COLOR)
    ax.set_facecolor(BACKGROUND_COLOR)
    ax.axis("off")

    # Title
    ax.text(
        0.5, 1.0,
        "Key Takeaways",
        ha="center", va="top",
        fontsize=18, fontweight="bold",
        color=HEADER_COLOR,
        transform=ax.transAxes,
    )
    ax.text(
        0.5, 0.93,
        company_name,
        ha="center", va="top",
        fontsize=11,
        color=TEXT_COLOR,
        transform=ax.transAxes,
        alpha=0.7,
    )

    # Takeaway items
    y_start = 0.83
    item_height = 0.82 / (n + 0.5) if n > 0 else 0.15

    for i, ta in enumerate(takeaways[:5]):
        y_pos = y_start - i * item_height

        # Number badge
        badge = mpatches.Circle(
            (0.035, y_pos),
            0.025,
            color=HEADER_COLOR,
            transform=ax.transAxes,
            zorder=3,
        )
        ax.add_patch(badge)
        ax.text(
            0.035, y_pos,
            str(i + 1),
            ha="center", va="center",
            fontsize=10, fontweight="bold",
            color="white",
            transform=ax.transAxes,
            zorder=4,
        )

        # Title
        ax.text(
            0.075, y_pos + 0.012,
            ta.title,
            ha="left", va="center",
            fontsize=10, fontweight="bold",
            color=TEXT_COLOR,
            transform=ax.transAxes,
        )

        # Justification (wrapped)
        just_wrapped = "\n".join(textwrap.wrap(ta.justification, width=90))
        ax.text(
            0.075, y_pos - 0.012,
            just_wrapped,
            ha="left", va="center",
            fontsize=8,
            color=TEXT_COLOR,
            transform=ax.transAxes,
            alpha=0.8,
        )

        # Citation URL (first)
        if ta.citations:
            cite = ta.citations[0]
            url_short = (cite.url or "")[:80]
            date_str = f" ({cite.published_date})" if cite.published_date else ""
            ax.text(
                0.075, y_pos - 0.030,
                f"Source: {url_short}{date_str}",
                ha="left", va="center",
                fontsize=6.5,
                color=HEADER_COLOR,
                transform=ax.transAxes,
                alpha=0.75,
            )

        # Separator line
        if i < n - 1:
            ax.axhline(
                y=y_pos - item_height * 0.45,
                xmin=0.02, xmax=0.98,
                color=TEXT_COLOR, alpha=0.1, linewidth=0.5,
                transform=ax.transAxes,
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(output_path), dpi=150, bbox_inches="tight", facecolor=BACKGROUND_COLOR)
    plt.close(fig)
    return output_path
