"""Agency-grade Streamlit styling (NYC DOT SIM) — enhanced v2."""

from __future__ import annotations

import streamlit as st

AGENCY_CSS = """
<style>
  /* ===== Skip link (a11y) ===== */
  .mc-skip {
    position: absolute; left: -9999px; z-index: 9999;
    padding: 8px 16px; background: #003366; color: #fff;
    text-decoration: none; border-radius: 4px;
  }
  .mc-skip:focus { left: 12px; top: 12px; }

  /* ===== Agency header ===== */
  .mc-header {
    border-bottom: 3px solid #f4c430;
    padding-bottom: 0.75rem;
    margin-bottom: 1rem;
    background: linear-gradient(135deg, #0a1628 0%, #0d2042 50%, #0a1628 100%);
    padding: 1rem 1.25rem;
    border-radius: 8px;
  }
  .mc-header h1 {
    color: #e8eef4; font-size: 1.85rem; margin: 0;
    text-shadow: 0 1px 4px rgba(0,0,0,0.4);
    letter-spacing: -0.5px;
  }
  .mc-subtitle { color: #9eb3c7; font-size: 0.95rem; margin-top: 0.25rem; }

  /* ===== Status badges ===== */
  .mc-badge {
    display: inline-block; padding: 3px 12px;
    border-radius: 12px; font-size: 0.75rem;
    font-weight: 700; margin-right: 6px; letter-spacing: 0.5px;
  }
  .mc-badge-live {
    background: linear-gradient(135deg, #1e5631, #267341);
    color: #b8f0c8;
    box-shadow: 0 1px 4px rgba(30, 86, 49, 0.5);
  }
  .mc-badge-demo {
    background: linear-gradient(135deg, #5c4a00, #7a6200);
    color: #ffe08a;
  }
  .mc-badge-warn {
    background: linear-gradient(135deg, #5c2e00, #7a3d00);
    color: #ffc9a0;
  }

  /* ===== Readiness bars ===== */
  .mc-bar-wrap {
    background: #2a3544; border-radius: 6px;
    height: 12px; margin: 4px 0 14px;
    overflow: hidden; box-shadow: inset 0 1px 3px rgba(0,0,0,0.3);
  }
  .mc-bar-fill {
    background: linear-gradient(90deg, #003366, #0066cc, #f4c430);
    height: 100%; border-radius: 6px;
    transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  }
  .mc-bar-fill-warn {
    background: linear-gradient(90deg, #5c2e00, #cc6600);
  }
  .mc-bar-fill-ok {
    background: linear-gradient(90deg, #1e5631, #27ae60);
  }
  .mc-axis-label {
    font-size: 0.82rem; display: flex;
    justify-content: space-between; color: #c5d4e3; margin-top: 4px;
  }

  /* ===== Metric cards ===== */
  div[data-testid="stMetric"] {
    background: #1a2332;
    border: 1px solid #2a3544;
    border-radius: 10px;
    padding: 0.75rem 1rem;
    transition: border-color 0.2s;
  }
  div[data-testid="stMetric"]:hover {
    border-color: #3a4d6a;
  }
  div[data-testid="stMetricLabel"] {
    font-size: 0.78rem !important;
    color: #8fa3bc !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  div[data-testid="stMetricValue"] {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: #e8eef4 !important;
  }

  /* ===== Dataframe ===== */
  div[data-testid="stDataFrame"] {
    border: 1px solid #2a3544;
    border-radius: 8px;
    overflow: hidden;
  }

  /* ===== Quality severity colors ===== */
  .quality-critical { color: #ff4444; font-weight: 700; }
  .quality-warn { color: #ff9900; font-weight: 600; }
  .quality-ok { color: #00cc66; }
  .quality-info { color: #66aaff; }

  /* ===== Accessibility ===== */
  @media (prefers-reduced-motion: reduce) {
    .mc-bar-fill { transition: none; }
  }
  @media (prefers-contrast: high) {
    .mc-header { background: #000; border-bottom-color: #fff; }
    .mc-header h1 { color: #fff; }
  }

  /* ===== Container borders ===== */
  div[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: #2a3544 !important;
    border-radius: 10px !important;
  }

  /* ===== Sidebar ===== */
  section[data-testid="stSidebar"] {
    background: #0d1b2a;
    border-right: 1px solid #1e3050;
  }
  section[data-testid="stSidebar"] .stRadio > label {
    color: #c5d4e3 !important;
  }
</style>
"""


def inject_theme() -> None:
    st.markdown(AGENCY_CSS, unsafe_allow_html=True)


def render_skip_link() -> None:
    st.markdown(
        '<a class="mc-skip" href="#main-content">Skip to main content</a>',
        unsafe_allow_html=True,
    )


def render_agency_header(*, demo: bool, live_auth: bool) -> None:
    if demo:
        badge = '<span class="mc-badge mc-badge-demo">⚠ DEMO DATA</span>'
    elif live_auth:
        badge = '<span class="mc-badge mc-badge-live">● LIVE SOCRATA</span>'
    else:
        badge = '<span class="mc-badge mc-badge-warn">⚡ PUBLIC TIER</span>'

    st.markdown(
        f"""
        <div class="mc-header">
          <h1 id="main-content">🚧 Manhattan Mission Control</h1>
          <p class="mc-subtitle">
            NYC DOT Sidewalk Inspection &amp; Management (SIM) · Analyst Workspace v2
          </p>
          {badge}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_readiness_bars(axis_scores: dict[str, float]) -> None:
    for axis, score in sorted(axis_scores.items()):
        pct = min(100.0, float(score))
        label = axis.replace("_", " ").title()

        if pct >= 80:
            bar_class = "mc-bar-fill mc-bar-fill-ok"
        elif pct >= 50:
            bar_class = "mc-bar-fill"
        else:
            bar_class = "mc-bar-fill mc-bar-fill-warn"

        icon = "✅" if pct >= 80 else ("⚠️" if pct >= 50 else "❌")

        st.markdown(
            f"""
            <div class="mc-axis-label" aria-label="{label} readiness {pct:.0f} percent">
              <span>{icon} {label}</span>
              <span style="font-weight:700;color:{'#27ae60' if pct >= 80 else ('#f39c12' if pct >= 50 else '#e74c3c')}">{pct:.0f}%</span>
            </div>
            <div class="mc-bar-wrap"
                 role="progressbar"
                 aria-valuenow="{pct:.0f}"
                 aria-valuemin="0"
                 aria-valuemax="100"
                 aria-label="{label}: {pct:.0f}%">
              <div class="{bar_class}" style="width:{pct}%;"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_quality_badge(score: float) -> str:
    """Return an HTML badge for a quality score."""
    if score >= 80:
        return f'<span class="mc-badge mc-badge-live">{score:.0f}/100</span>'
    if score >= 60:
        return f'<span class="mc-badge mc-badge-demo">{score:.0f}/100</span>'
    return f'<span class="mc-badge mc-badge-warn">{score:.0f}/100</span>'
