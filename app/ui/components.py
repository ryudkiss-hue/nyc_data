"""Reusable presentation components for Manhattan Mission Control.

KPI cards with inline sparklines, responsive metric grids, section headers,
status pills, skeleton loaders, and dataframe sparkline column configs. All
components degrade gracefully and use color-blind-safe semantics with icons
(never color alone) per WCAG 2.2.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from app.ui.palettes import severity_color


# ---------------------------------------------------------------------------
# Section header
# ---------------------------------------------------------------------------
def section_header(title: str, subtitle: str = "", *, icon: str = "") -> None:
    """Consistent section header with optional icon and subtitle."""
    prefix = f"{icon} " if icon else ""
    st.markdown(
        f"""
        <div class="mc-section-header">
          <h3>{prefix}{title}</h3>
          {f'<p class="mc-section-sub">{subtitle}</p>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Status pill (icon + color, never color alone)
# ---------------------------------------------------------------------------
_PILL_ICON = {"critical": "❌", "warn": "⚠️", "ok": "✅", "info": "ℹ️", "neutral": "•"}


def status_pill(label: str, level: str = "neutral") -> str:
    """Return HTML for an accessible status pill (icon + color + text)."""
    color = severity_color(level)
    icon = _PILL_ICON.get(level.lower(), "•")
    return (
        f'<span class="mc-pill" style="--pill:{color}" '
        f'role="status" aria-label="{level}: {label}">{icon} {label}</span>'
    )


# ---------------------------------------------------------------------------
# KPI cards (responsive grid, optional sparkline + delta)
# ---------------------------------------------------------------------------
def kpi_card(
    label: str,
    value: str | int | float,
    *,
    delta: str | None = None,
    delta_good: bool = True,
    spark: list[float] | None = None,
    icon: str = "",
    help_text: str = "",
) -> None:
    """Single KPI card with big value, optional delta and inline sparkline."""
    from app.ui.charts import sparkline

    delta_html = ""
    if delta is not None:
        arrow = "▲" if delta_good else "▼"
        color = "#10B981" if delta_good else "#EF4444"
        delta_html = (
            f'<span class="mc-kpi-delta" style="color:{color}" '
            f'aria-label="change {delta}">{arrow} {delta}</span>'
        )
    title_attr = f' title="{help_text}"' if help_text else ""
    st.markdown(
        f"""
        <div class="mc-kpi"{title_attr}>
          <div class="mc-kpi-label">{f'{icon} ' if icon else ''}{label}</div>
          <div class="mc-kpi-value">{value}{delta_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if spark and len(spark) > 1:
        fig = sparkline(spark)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def kpi_row(cards: list[dict[str, Any]], *, columns: int | None = None) -> None:
    """Render a responsive row of KPI cards.

    Each dict supports keys: label, value, delta, delta_good, spark, icon, help_text.
    Columns auto-fit; pass `columns` to force a count.
    """
    if not cards:
        return
    n = columns or min(len(cards), 4)
    cols = st.columns(n)
    for i, card in enumerate(cards):
        with cols[i % n]:
            kpi_card(**card)


# ---------------------------------------------------------------------------
# Skeleton loader
# ---------------------------------------------------------------------------
def skeleton(lines: int = 3, *, height: int = 18) -> None:
    """Render a low-contrast skeleton placeholder while data loads."""
    bars = "".join(
        f'<div class="mc-skeleton-bar" style="height:{height}px;'
        f'width:{90 - i * 12}%"></div>'
        for i in range(max(1, lines))
    )
    st.markdown(f'<div class="mc-skeleton">{bars}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Dataframe sparkline column config
# ---------------------------------------------------------------------------
def sparkline_columns(
    df: pd.DataFrame,
    *,
    trend_cols: dict[str, str] | None = None,
    progress_cols: dict[str, tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """Build a `column_config` dict adding inline charts to st.dataframe.

    trend_cols: {column_name: "line"|"bar"} → LineChartColumn / BarChartColumn
    progress_cols: {column_name: (min, max)} → ProgressColumn
    """
    config: dict[str, Any] = {}
    for col, kind in (trend_cols or {}).items():
        if col not in df.columns:
            continue
        if kind == "bar":
            config[col] = st.column_config.BarChartColumn(col.replace("_", " ").title())
        else:
            config[col] = st.column_config.LineChartColumn(col.replace("_", " ").title())
    for col, (lo, hi) in (progress_cols or {}).items():
        if col not in df.columns:
            continue
        config[col] = st.column_config.ProgressColumn(
            col.replace("_", " ").title(),
            min_value=lo,
            max_value=hi,
            format="%.0f",
        )
    return config


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------
def empty_state(title: str, body: str = "", *, icon: str = "📭", action_label: str = "", action_key: str = "") -> bool:
    """Friendly empty state. Returns True if the optional action button is clicked."""
    st.markdown(
        f"""
        <div class="mc-empty">
          <div class="mc-empty-icon">{icon}</div>
          <div class="mc-empty-title">{title}</div>
          {f'<div class="mc-empty-body">{body}</div>' if body else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )
    if action_label:
        return st.button(action_label, key=action_key or f"empty_{title}", use_container_width=True)
    return False
