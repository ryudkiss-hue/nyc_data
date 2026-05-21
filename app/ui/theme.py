"""Agency-grade Streamlit styling (NYC DOT SIM)."""

from __future__ import annotations

import streamlit as st

AGENCY_CSS = """
<style>
  /* Skip link */
  .mc-skip { position:absolute; left:-9999px; z-index:9999; padding:8px 16px;
    background:#003366; color:#fff; text-decoration:none; border-radius:4px; }
  .mc-skip:focus { left:12px; top:12px; }
  /* Header */
  .mc-header { border-bottom:2px solid #f4c430; padding-bottom:0.75rem; margin-bottom:1rem; }
  .mc-header h1 { color:#e8eef4; font-size:1.75rem; margin:0; }
  .mc-subtitle { color:#9eb3c7; font-size:0.95rem; margin-top:0.25rem; }
  .mc-badge { display:inline-block; padding:2px 10px; border-radius:12px;
    font-size:0.75rem; font-weight:600; margin-right:6px; }
  .mc-badge-live { background:#1e5631; color:#b8f0c8; }
  .mc-badge-demo { background:#5c4a00; color:#ffe08a; }
  .mc-badge-warn { background:#5c2e00; color:#ffc9a0; }
  /* Readiness bars */
  .mc-bar-wrap { background:#2a3544; border-radius:6px; height:10px; margin:4px 0 12px; overflow:hidden; }
  .mc-bar-fill { background:linear-gradient(90deg,#003366,#f4c430); height:100%; border-radius:6px;
    transition:width 0.3s ease; }
  .mc-axis-label { font-size:0.82rem; display:flex; justify-content:space-between; color:#c5d4e3; }
  /* Cards */
  div[data-testid="stMetric"] {
    background:#1a2332; border:1px solid #2a3544; border-radius:8px; padding:0.5rem;
  }
  @media (prefers-reduced-motion: reduce) {
    .mc-bar-fill { transition: none; }
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
    badge = (
        '<span class="mc-badge mc-badge-demo">DEMO DATA</span>'
        if demo
        else (
            '<span class="mc-badge mc-badge-live">LIVE SOCRATA</span>'
            if live_auth
            else '<span class="mc-badge mc-badge-warn">PUBLIC TIER</span>'
        )
    )
    st.markdown(
        f"""
        <div class="mc-header">
          <h1 id="main-content">Manhattan Mission Control</h1>
          <p class="mc-subtitle">NYC DOT Sidewalk Inspection &amp; Management (SIM) · Analyst workspace</p>
          {badge}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_readiness_bars(axis_scores: dict[str, float]) -> None:
    for axis, score in sorted(axis_scores.items()):
        pct = min(100.0, float(score))
        label = axis.replace("_", " ").title()
        st.markdown(
            f"""
            <div class="mc-axis-label" aria-label="{label} readiness {pct:.0f} percent">
              <span>{label}</span><span>{pct:.0f}%</span>
            </div>
            <div class="mc-bar-wrap" role="progressbar" aria-valuenow="{pct:.0f}" aria-valuemin="0" aria-valuemax="100">
              <div class="mc-bar-fill" style="width:{pct}%;"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
