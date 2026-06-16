"""Visualization utilities for data exploration and reporting.

This module provides lightweight chart generation that works without a display
server by defaulting to the matplotlib Agg backend. Charts can be saved to
files (PNG, SVG, PDF) or returned as base64-encoded strings for embedding in
HTML reports or Streamlit apps.

Supported chart types:
- Histogram with optional KDE overlay
- Bar chart (horizontal and vertical)
- Correlation heatmap
- Time series line chart with trend line
- Distribution comparison (box plots)
- Quality dashboard (missing values, duplicates summary)
"""

from __future__ import annotations

import base64
import io
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np  # type: ignore[import]
import pandas as pd  # type: ignore[import]

from .branding import DOT_BLACK, DOT_BLUE, MATPLOTLIB_STYLE, WCAG_PALETTE


def _get_plt():
    """Import matplotlib with Agg backend (no display required)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # Apply DOT Industrial Branding
    plt.rcParams.update(MATPLOTLIB_STYLE)
    return plt

@dataclass
class ChartResult:
    """Container for a generated chart with statistical metadata."""
    title: str
    chart_type: str
    path: str | None = None
    base64_png: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

def _finalize(fig, title: str, chart_type: str, path: str | None = None, metadata: dict[str, Any] | None = None) -> ChartResult:
    """Save or encode a matplotlib figure and return a ChartResult."""
    plt = _get_plt()
    fig.tight_layout()
    res_metadata = metadata or {}
    
    if path:
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return ChartResult(title=title, chart_type=chart_type, path=path, metadata=res_metadata)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    return ChartResult(title=title, chart_type=chart_type, base64_png=b64, metadata=res_metadata)

# ---------------------------------------------------------------------------
# Histogram
# ---------------------------------------------------------------------------

def histogram(
    df: pd.DataFrame,
    column: str,
    bins: int = 30,
    title: str | None = None,
    path: str | None = None,
    kde: bool = False,
) -> ChartResult:
    """Generate a histogram for a numeric column."""
    plt = _get_plt()
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(series, bins=bins, edgecolor="white", alpha=0.8, color=DOT_BLUE)
    
    metadata = {
        "mean": float(series.mean()),
        "std": float(series.std()),
        "count": int(len(series)),
        "skew": float(series.skew()),
        "kurtosis": float(series.kurtosis()),
    }

    if kde and len(series) > 2:
        try:
            from scipy.stats import gaussian_kde
            xs = np.linspace(float(series.min()), float(series.max()), 200)
            density = gaussian_kde(series)(xs)
            ax2 = ax.twinx()
            ax2.plot(xs, density, color="#D63384", linewidth=2) # Contrast color
            ax2.set_ylabel("Density")
        except ImportError:
            pass  # scipy not available
    chart_title = title or f"Histogram: {column}"
    ax.set_title(chart_title)
    ax.set_xlabel(column)
    ax.set_ylabel("Count")
    return _finalize(fig, chart_title, "histogram", path, metadata=metadata)

# ---------------------------------------------------------------------------
# Bar Chart
# ---------------------------------------------------------------------------

def bar_chart(
    df: pd.DataFrame,
    column: str,
    top_n: int = 20,
    horizontal: bool = False,
    title: str | None = None,
    path: str | None = None,
) -> ChartResult:
    """Generate a bar chart showing value counts for a column."""
    plt = _get_plt()
    counts = df[column].value_counts().head(top_n)
    fig, ax = plt.subplots(figsize=(8, max(5, len(counts) * 0.35) if horizontal else 5))
    
    metadata = {
        "top_categories": counts.to_dict(),
        "total_unique": int(df[column].nunique()),
    }

    if horizontal:
        ax.barh(counts.index.astype(str), counts.values, color=DOT_BLUE)
        ax.set_xlabel("Count")
        ax.invert_yaxis()
    else:
        ax.bar(counts.index.astype(str), counts.values, color=DOT_BLUE)
        ax.set_ylabel("Count")
        plt.xticks(rotation=45, ha="right")
    chart_title = title or f"Value Counts: {column}"
    ax.set_title(chart_title)
    return _finalize(fig, chart_title, "bar_chart", path, metadata=metadata)

# ---------------------------------------------------------------------------
# Correlation Heatmap
# ---------------------------------------------------------------------------

def correlation_heatmap(
    df: pd.DataFrame,
    method: str = "pearson",
    title: str | None = None,
    path: str | None = None,
) -> ChartResult:
    """Generate a correlation heatmap for numeric columns."""
    plt = _get_plt()
    numeric = df.select_dtypes(include="number")
    corr = numeric.corr(method=method)
    fig, ax = plt.subplots(figsize=(max(8, len(corr.columns) * 0.8), max(6, len(corr.columns) * 0.7)))
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(corr.columns, fontsize=8)
    # annotate cells
    for i in range(len(corr)):
        for j in range(len(corr)):
            val = corr.iloc[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=7,
                        color="white" if abs(val) > 0.6 else "black")
    fig.colorbar(im, ax=ax, shrink=0.8)
    chart_title = title or f"Correlation Heatmap ({method})"
    ax.set_title(chart_title)
    
    metadata = {
        "matrix": corr.to_dict(),
        "columns": list(corr.columns),
    }
    return _finalize(fig, chart_title, "heatmap", path, metadata=metadata)

# ---------------------------------------------------------------------------
# Time Series Line Chart
# ---------------------------------------------------------------------------

def time_series_chart(
    df: pd.DataFrame,
    date_column: str,
    value_column: str,
    resample_freq: str = "M",
    agg: str = "mean",
    show_trend: bool = True,
    title: str | None = None,
    path: str | None = None,
) -> ChartResult:
    """Generate a time series line chart with optional trend line."""
    plt = _get_plt()
    tmp = df[[date_column, value_column]].copy()
    tmp[date_column] = pd.to_datetime(tmp[date_column], errors="coerce")
    tmp[value_column] = pd.to_numeric(tmp[value_column], errors="coerce")
    tmp = tmp.dropna().set_index(date_column).sort_index()

    resampled = tmp.resample(resample_freq).agg(agg)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(resampled.index, resampled[value_column], marker="o", markersize=3, linewidth=1.5, color=DOT_BLUE)

    metadata = {
        "resample_freq": resample_freq,
        "agg_method": agg,
        "n_points": len(resampled),
    }

    if show_trend and len(resampled) >= 3:
        x_ord = np.arange(len(resampled), dtype=float)
        y = resampled[value_column].values.astype(float)
        valid = ~np.isnan(y)
        if valid.sum() >= 2:
            coeffs = np.polyfit(x_ord[valid], y[valid], 1)
            trend_y = np.polyval(coeffs, x_ord)
            ax.plot(resampled.index, trend_y, "--", color="#D63384", linewidth=1.5, label="Trend")
            ax.legend()
            metadata["trend_slope"] = float(coeffs[0])

    chart_title = title or f"Time Series: {value_column} ({agg} by {resample_freq})"
    ax.set_title(chart_title)
    ax.set_xlabel("Date")
    ax.set_ylabel(value_column)
    fig.autofmt_xdate()
    return _finalize(fig, chart_title, "time_series", path, metadata=metadata)

# ---------------------------------------------------------------------------
# Box Plot Comparison
# ---------------------------------------------------------------------------

def box_plot(
    df: pd.DataFrame,
    columns: Sequence[str],
    title: str | None = None,
    path: str | None = None,
) -> ChartResult:
    """Generate side-by-side box plots for the given numeric columns."""
    plt = _get_plt()
    data = [pd.to_numeric(df[c], errors="coerce").dropna().values for c in columns]
    fig, ax = plt.subplots(figsize=(max(6, len(columns) * 1.5), 5))
    bp = ax.boxplot(data, labels=columns, patch_artist=True)
    
    metadata = {}
    for i, col in enumerate(columns):
        if len(data[i]) > 0:
            metadata[col] = {
                "median": float(np.median(data[i])),
                "q1": float(np.percentile(data[i], 25)),
                "q3": float(np.percentile(data[i], 75)),
            }

    for i, patch in enumerate(bp["boxes"]):
        patch.set_facecolor(WCAG_PALETTE[i % len(WCAG_PALETTE)])
    chart_title = title or "Distribution Comparison"
    ax.set_title(chart_title)
    ax.set_ylabel("Value")
    return _finalize(fig, chart_title, "box_plot", path, metadata=metadata)

# ---------------------------------------------------------------------------
# Quality Dashboard
# ---------------------------------------------------------------------------

@dataclass
class QualityDashboard:
    """Visual quality summary for a DataFrame."""
    missing_chart: ChartResult
    completeness_score: float
    total_cells: int
    missing_cells: int

def quality_dashboard(
    df: pd.DataFrame,
    title: str | None = None,
    path_prefix: str | None = None,
) -> QualityDashboard:
    """Generate a quality overview chart showing missing values per column."""
    plt = _get_plt()
    missing = df.isnull().sum()
    missing = missing[missing > 0].sort_values(ascending=True)
    total_cells = df.shape[0] * df.shape[1]
    missing_cells = int(df.isnull().sum().sum())
    completeness = round((1 - missing_cells / max(total_cells, 1)) * 100, 2)

    fig, ax = plt.subplots(figsize=(8, max(4, len(missing) * 0.4)))
    if len(missing) > 0:
        # High contrast colors for quality
        colors = ["#DC3545" if v > df.shape[0] * 0.3 else "#E67E22" if v > df.shape[0] * 0.1 else "#198754" for v in missing.values]
        ax.barh(missing.index.astype(str), missing.values, color=colors)
        ax.set_xlabel("Missing Values")
        # add percentage labels
        for i, (v, col) in enumerate(zip(missing.values, missing.index)):
            pct = v / df.shape[0] * 100
            ax.text(v + 0.5, i, f"{pct:.1f}%", va="center", fontsize=8)
    else:
        ax.text(0.5, 0.5, "No missing values detected", transform=ax.transAxes,
                ha="center", va="center", fontsize=14, color="#198754")

    chart_title = title or f"Data Quality: {completeness}% Complete"
    ax.set_title(chart_title)
    missing_path = f"{path_prefix}_missing.png" if path_prefix else None
    
    metadata = {
        "completeness_score": completeness,
        "total_cells": total_cells,
        "missing_cells": missing_cells,
        "missing_by_column": missing.to_dict(),
    }
    
    missing_chart = _finalize(fig, chart_title, "quality_missing", missing_path, metadata=metadata)

    return QualityDashboard(
        missing_chart=missing_chart,
        completeness_score=completeness,
        total_cells=total_cells,
        missing_cells=missing_cells,
    )

def dataframe_to_pdf(
    df: pd.DataFrame,
    path: str,
    title: str = "Data Report",
) -> str:
    """Export a DataFrame to PDF, falling back to HTML when PDF libs are unavailable."""
    from pathlib import Path

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    def _html() -> str:
        table = df.to_html(index=False, escape=True)
        return (
            f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<title>{title}</title></head><body><h1>{title}</h1>{table}</body></html>"
        )

    try:
        from weasyprint import HTML  # type: ignore

        pdf_path = out if out.suffix.lower() == ".pdf" else out.with_suffix(".pdf")
        HTML(string=_html()).write_pdf(str(pdf_path))
        return str(pdf_path)
    except Exception:
        html_path = out if out.suffix.lower() == ".html" else out.with_suffix(".html")
        html_path.write_text(_html(), encoding="utf-8")
        return str(html_path)
