"""Agency-grade Streamlit styling (NYC DOT SIM) — enhanced v2."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

import streamlit as st

# ---------------------------------------------------------------------------
# NYC DOT brand constants
# ---------------------------------------------------------------------------
NYC_BLUE = "#003087"
NYC_ORANGE = "#FF6319"
NYC_GREEN = "#00A859"
SIDEBAR_WIDTH = 280

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

  /* ===== Skeleton loading placeholders ===== */
  .mc-skeleton-row {
    background: linear-gradient(90deg, #1e2d3d 25%, #2a3f52 50%, #1e2d3d 75%);
    background-size: 200% 100%;
    animation: mc-shimmer 1.4s infinite;
    border-radius: 6px;
    height: 1.2rem;
    margin-bottom: 0.5rem;
  }
  @keyframes mc-shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }
  @media (prefers-reduced-motion: reduce) {
    .mc-skeleton-row { animation: none; background: #1e2d3d; }
  }

  /* ===== Empty state ===== */
  .mc-empty-state {
    text-align: center; padding: 2.5rem 1rem;
    border: 2px dashed #2a3544; border-radius: 12px;
    margin: 1rem 0;
  }
  .mc-empty-icon { font-size: 3rem; margin-bottom: 0.75rem; }
  .mc-empty-msg { color: #8fa3bc; font-size: 1rem; margin-bottom: 1rem; }

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


@contextmanager
def render_skeleton_placeholder(n_rows: int = 3) -> Generator[None, None, None]:
    """Context manager that renders skeleton loading rows, then clears them.

    Usage::

        with render_skeleton_placeholder(n_rows=4):
            time.sleep(2)  # replaced by real content after yield
        st.write("Real content here")
    """
    skeleton_html = "".join(
        f'<div class="mc-skeleton-row" style="width:{90 - (i * 10) % 30}%;"></div>'
        for i in range(n_rows)
    )
    placeholder = st.empty()
    placeholder.markdown(
        f'<div style="padding:0.5rem 0">{skeleton_html}</div>',
        unsafe_allow_html=True,
    )
    try:
        yield
    finally:
        placeholder.empty()


def render_empty_state(
    message: str = "No data loaded yet",
    action_label: str = "Load Data",
    action_key: str = "empty_state_action",
) -> None:
    """Display an icon + message empty state with an action button.

    Sets ``st.session_state[action_key] = True`` when the button is clicked.
    """
    st.markdown(
        f"""
        <div class="mc-empty-state">
          <div class="mc-empty-icon">📭</div>
          <div class="mc-empty-msg">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        if st.button(action_label, type="primary", use_container_width=True, key=action_key):
            st.session_state[action_key] = True
