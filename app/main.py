"""
⚠️ ARCHIVED ENTRY POINT (Superseded by app/app.py)

This file is legacy and no longer maintained. Use 'streamlit run app/app.py' instead.

Manhattan Mission Control: Elite Operational Engine (v2.0 - SaaS Grade)
A unified, premium Streamlit application for NYC DOT SIM Project Analysts.

MIGRATION: Run the canonical app with:
  streamlit run app/app.py
Or use the shim:
  python main.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import streamlit as st

# Aggressively remove ghost environment paths
ghost_paths = [p for p in sys.path if "Downloads" in p and "nyc_data" in p]
for gp in ghost_paths:
    sys.path.remove(gp)

# Bulletproof path resolution to ensure the local 'src' directory is prioritized
_src_path = str((Path(__file__).resolve().parent.parent / "src").absolute())
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

# Force clear sys.modules for socrata_toolkit to ensure clean reload from new path
keys_to_delete = [k for k in sys.modules if k.startswith("socrata_toolkit")]
for k in keys_to_delete:
    del sys.modules[k]


warnings.filterwarnings("ignore")

# ==========================================
# --- CONFIGURATION & THEMING ---
# ==========================================

st.set_page_config(
    page_title="Manhattan Mission Control",
    page_icon="🗽",
    layout="wide",
    initial_sidebar_state="expanded",
)

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent"

# NYC Mission Control Palette (Elite Dark Mode)
COLORS = {
    "primary": "#22D3EE",      # Mission Cyan
    "accent": "#FDE047",       # Soft Gold
    "success": "#34D399",      # Emerald Green
    "danger": "#F87171",       # Coral Red
    "background": "#0F172A",   # Slate 900 (Main BG)
    "surface": "#1E293B",      # Slate 800 (Card Surface)
    "card_bg": "rgba(30, 41, 59, 0.7)", # Frosted Slate
    "text": "#F8FAF8",         # Off-White
    "text_muted": "#94A3B8",   # Slate 400
    "border": "rgba(255, 255, 255, 0.1)",
    "confidence": "rgba(34, 211, 238, 0.1)",
}

BOROUGH_COORDS = {
    "MANHATTAN": [40.7831, -73.9712],
    "BROOKLYN": [40.6782, -73.9442],
    "QUEENS": [40.7282, -73.7949],
    "BRONX": [40.8448, -73.8648],
    "STATEN ISLAND": [40.5795, -74.1502],
    "UNKNOWN": [40.7128, -74.0060],
}

def inject_custom_css():
    st.markdown(f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

            :root {{
                --transition-fast: all 0.2s ease-out;
            }}

            html, body, [class*="css"]  {{
                font-family: 'Inter', sans-serif !important;
                color: {COLORS['text']};
            }}

            /* Hide Streamlit Branding */
            #MainMenu {{visibility: hidden;}}
            footer {{visibility: hidden;}}
            header {{visibility: hidden;}}

            /* Breathable Layout */
            .block-container {{
                padding: clamp(2rem, 5vw, 4rem);
                max-width: 1400px;
            }}

            /* Elite Dark Mode KPI Cards */
            .kpi-card {{
                background: {COLORS['card_bg']};
                backdrop-filter: blur(8px);
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
                transition: var(--transition-fast);
                min-height: 120px;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }}
            .kpi-card:hover {{
                transform: translateY(-4px) scale(1.02);
                border-color: {COLORS['primary']};
                box-shadow: 0 10px 20px -5px rgba(0, 0, 0, 0.3);
            }}
            .kpi-label {{
                font-size: 0.75rem;
                font-weight: 600;
                color: {COLORS['text_muted']};
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: 0.25rem;
            }}
            .kpi-value {{
                font-size: 2rem;
                font-weight: 800;
                color: {COLORS['primary']};
                line-height: 1.1;
            }}

            /* Sidebar Refinement */
            [data-testid="stSidebar"] {{
                background-color: #0B1120 !important;
                border-right: 1px solid {COLORS['border']};
            }}

            /* Global Scrollbar */
            ::-webkit-scrollbar {{ width: 6px; }}
            ::-webkit-scrollbar-thumb {{ background: {COLORS['surface']}; border-radius: 10px; }}

            /* Call to Action Button */
            .cta-container {{
                background: linear-gradient(90deg, rgba(34, 211, 238, 0.1) 0%, rgba(34, 211, 238, 0) 100%);
                border-left: 4px solid {COLORS['primary']};
                padding: 2rem;
                border-radius: 8px;
                margin-top: 4rem;
                text-align: center;
            }}
        </style>
    """, unsafe_allow_html=True)

# ... (rest of session state and data ingestion functions remain identical) ...

def _init_state():
    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False
    if "theme" not in st.session_state:
        st.session_state.theme = "light"

def render_kpi_card(title: str, value: str, tooltip: str = ""):
    st.markdown(f'''
    <div class="kpi-card" title="{tooltip}">
        <div class="kpi-label">{title}</div>
        <div class="kpi-value">{value}</div>
    </div>
    ''', unsafe_allow_html=True)

def main():
    _init_state()
    inject_custom_css()

    with st.sidebar:
        st.markdown(f"<h2 style='color:{COLORS['primary']}; margin:0;'>🗽 Mission Control</h2>", unsafe_allow_html=True)
        st.caption("Bayesian Analytics Engine v3.1")
        st.write("")

        nav_selection = st.radio("Navigation", [
            "🏠 Executive Dashboard",
            "🗺️ Geospatial Intelligence",
            "🧮 Data Science & MCMC",
            "🏗️ Engineering & Equity",
            "⚙️ Settings & Pipeline",
            "🤖 AI Copilot"
        ], label_visibility="collapsed")

        st.divider()

    # ==========================================
    # --- ROUTER LOGIC ---
    # ==========================================

    if not st.session_state.pipeline_run and nav_selection != "⚙️ Settings & Pipeline":
        st.markdown(f"<h1 style='text-align:center; font-size:3.5rem; font-weight:800; color:{COLORS['primary']}; padding-top: 4rem;'>Manhattan Mission Control</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; font-size:1.2rem; color:#94A3B8; margin-bottom: 3rem;'>Unified Bayesian Intelligence & Infrastructure Management Hub</p>", unsafe_allow_html=True)

        st.divider()

        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        with kpi_col1: render_kpi_card("Active Datasets", "26", tooltip="Live SODA2 Endpoints")
        with kpi_col2: render_kpi_card("System Health", "Optimal", tooltip="All Services Online")
        with kpi_col3: render_kpi_card("Pipeline", "Standby", tooltip="Awaiting Initialization")

        st.write("")
        st.write("")

        # Placeholder container for future analysis
        with st.container():
            st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True) # Spacer
            if st.button("🚀  INITIALIZE ANALYTICS ENGINE", use_container_width=True, type="primary"):
                st.session_state.pipeline_run = True # Direct jump for UX
                st.rerun()
            st.caption("<p style='text-align:center;'>Click above to configure your API keys and target SoQL queries.</p>", unsafe_allow_html=True)
        return

