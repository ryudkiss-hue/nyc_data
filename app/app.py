"""NYC DOT SIM Analyst Toolkit — Streamlit desktop application."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import streamlit as st

st.set_page_config(
    page_title="NYC DOT SIM Toolkit",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from app.analytics import run_all_workflows
from app.data_loader import (
    CACHE_TTL_SECONDS,
    WORKFLOW_DATASETS,
    demo_mode_enabled,
    fetch_datasets_for_keys,
    keys_for_workflow,
    load_manhattan_map_layers,
    token_status,
)
from app.ui.empty_states import frames_are_empty, render_empty_state
from app.ui.theme import inject_theme, render_agency_header, render_skip_link
from app.utils.i18n import render_language_selector, t
from app.views import home, publish, settings, workflows
from app.views.construction import render_construction_page
from app.views.contracts_dashboard import render_contracts_page
from app.views.data_discovery import render_data_discovery_page
from app.views.forecasting import render_forecasting_page
from app.views.gis_dashboard import render_gis_page

# Top-level navigation sections
_SECTIONS = {
    "🏠 Home":                   "home",
    "🏗️ Construction Lists":     "construction",
    "🗺️ GIS & Conflicts":        "gis",
    "📋 Contract Analytics":     "contracts",
    "📈 Forecasting":            "forecasting",
    "⚙️ Data Workflows":         "workflows",
    "📊 Advanced Analytics":     "advanced_analytics",
    "🔍 Data Discovery":         "discovery",
    "📚 Data Catalog":           "data_catalog",
    "📤 Publish":                "publish",
    "⚙️ Settings":               "settings",
}

WORKFLOW_KEYS = {
    "qa": "🔍 QA/QC & Inventory Ledger",
    "spatial": "🗺️ Spatial Conflict Detection",
    "contract": "📋 Contract & Dispatch Clearance",
    "productivity": "🚶 Productivity & ADA Progress",
    "quality": "🩺 Data Quality Dashboard",
}

# Sidebar groupings for collapsible expanders
_NAV_GROUPS = {
    "📊 Core Data": ["🏠 Home", "🏗️ Construction Lists"],
    "🗺️ Spatial": ["🗺️ GIS & Conflicts"],
    "📈 Analytics": [
        "📋 Contract Analytics",
        "📈 Forecasting",
        "⚙️ Data Workflows",
        "📊 Advanced Analytics",
    ],
    "🔧 Tools": [
        "🔍 Data Discovery",
        "📚 Data Catalog",
        "📤 Publish",
        "⚙️ Settings",
    ],
}


@contextmanager
def _spinner_view():
    with st.spinner("Loading view…"):
        yield


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Loading workflow datasets…")
def _load_workflow_frames(workflow_key: str, limit: int) -> dict:
    if workflow_key == "quality":
        all_keys: list[str] = []
        for v in WORKFLOW_DATASETS.values():
            all_keys.extend(v)
        return fetch_datasets_for_keys(tuple(dict.fromkeys(all_keys)), limit=limit)
    return fetch_datasets_for_keys(keys_for_workflow(workflow_key), limit=limit)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Loading full ingestion matrix…")
def _load_all_frames(limit: int) -> dict:
    from app.data_loader import DATASET_REGISTRY
    return fetch_datasets_for_keys(tuple(DATASET_REGISTRY.keys()), limit=limit)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Loading Manhattan map layers…")
def _load_map_layers(limit: int) -> dict:
    return load_manhattan_map_layers(limit=limit)


@st.cache_data(ttl=600, show_spinner="Running analyst workflows…")
def _run_workflows(frames: dict) -> dict:
    return run_all_workflows(frames)


def _sidebar_nav() -> tuple[str, dict]:
    """Render sidebar navigation. Returns (section_key, workflow_opts)."""
    with st.sidebar:
        render_language_selector()
        st.markdown("### 🏙️ NYC DOT · SIM")
        st.markdown("**Analyst Toolkit**")
        st.caption("Sidewalk Inspection Management")
        st.divider()

        # Dark mode toggle
        dark = st.toggle("🌙 Dark mode", key="dark_mode", value=False)
        if dark:
            st.markdown(
                """<style>
                .stApp { background-color: #1a1a2e; color: #e0e0e0; }
                .stSidebar { background-color: #16213e; }
                .stDataFrame { background-color: #1a1a2e; }
                div[data-testid="metric-container"] {
                    background-color: #16213e; border-radius: 8px; padding: 8px;
                }
                </style>""",
                unsafe_allow_html=True,
            )

        st.divider()

        # Collapsible sidebar navigation
        selected_label: str | None = None

        expand_flags = {
            "📊 Core Data": True,
            "🗺️ Spatial": False,
            "📈 Analytics": False,
            "🔧 Tools": False,
        }

        # Pre-expand the group containing the current active section
        current_nav = st.session_state.get("main_nav_section", "home")
        for group_name, labels in _NAV_GROUPS.items():
            for label in labels:
                if _SECTIONS.get(label) == current_nav:
                    expand_flags[group_name] = True

        for group_name, labels in _NAV_GROUPS.items():
            with st.expander(group_name, expanded=expand_flags[group_name]):
                choice = st.radio(
                    group_name,
                    labels,
                    label_visibility="collapsed",
                    key=f"nav_group_{group_name}",
                )
                if choice:
                    selected_label = choice

        # Determine active section from the last interacted radio
        # Fall back to session state if nothing was freshly picked
        if selected_label is not None:
            section = _SECTIONS.get(selected_label, "home")
            st.session_state["main_nav_section"] = section
        else:
            section = st.session_state.get("main_nav_section", "home")

        st.divider()

        wf_opts: dict = {"view_key": "qa", "row_limit": 10_000, "show_ingest": False}

        if section == "workflows":
            wf_labels = list(WORKFLOW_KEYS.values())
            view_label = st.radio("Workflow", wf_labels, index=0, key="wf_select")
            wf_opts["view_key"] = [k for k, v in WORKFLOW_KEYS.items() if v == view_label][0]
            wf_opts["row_limit"] = st.slider(
                "Max rows / dataset", 1_000, 50_000, 10_000, step=1_000
            )
            if demo_mode_enabled():
                st.info(t("demo_active"))
            if st.button(t("refresh_cache"), type="primary", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
            wf_opts["show_ingest"] = st.checkbox("Full ingestion matrix")

        st.divider()
        if st.button("🗑️ Clear Session", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.cache_data.clear()
            st.rerun()

        # Keyboard shortcuts help
        with st.expander("⌨️ Keyboard Shortcuts"):
            st.markdown(
                """
| Key | Action |
|-----|--------|
| `?` | This help |
| `r` | Refresh data |
| `d` | Toggle dark mode |
"""
            )

        # Quick-stats footer
        st.markdown("---")
        st.caption("NYC DOT · SIM Program  \nAnalyst Toolkit v2.0")

    return section, wf_opts


def _render_onboarding() -> None:
    """Show onboarding welcome panel on first run."""
    if not st.session_state.get("onboarding_done"):
        with st.sidebar.expander("👋 Welcome to NYC DOT SIM Toolkit", expanded=True):
            st.markdown(
                """**Quick Start:**
- 🏠 **Home** — KPI overview and system status
- 🗺️ **GIS** — Map inspections, detect conflicts
- 📋 **Contracts** — Violations, dismissals, tree damage
- 📈 **Forecasting** — Prediction and trends
- 🔍 **Data Discovery** — Query any Socrata dataset
- ⚙️ **Settings** — Configure API tokens and preferences
"""
            )
            if st.button("Got it, let's go!", key="onboarding_btn"):
                st.session_state["onboarding_done"] = True
                st.rerun()


def main() -> None:
    inject_theme()
    render_skip_link()

    # Persistent filter state
    if "filter_state" not in st.session_state:
        st.session_state["filter_state"] = {}

    _render_onboarding()
    section, wf_opts = _sidebar_nav()

    token = token_status()
    render_agency_header(
        demo=bool(token.get("demo_mode")),
        live_auth=bool(token["configured"] or token.get("key_pair")),
    )

    # Breadcrumb caption
    section_label = next((k for k, v in _SECTIONS.items() if v == section), section)
    st.caption(f"📍 {section_label}")

    # ------------------------------------------------------------------ #
    # Route to section
    # ------------------------------------------------------------------ #
    if section == "home":
        with _spinner_view():
            home.render_home_page()
        return

    if section == "construction":
        with _spinner_view():
            render_construction_page()
        return

    if section == "gis":
        with _spinner_view():
            render_gis_page()
        return

    if section == "contracts":
        with _spinner_view():
            render_contracts_page()
        return

    if section == "forecasting":
        with _spinner_view():
            render_forecasting_page()
        return

    if section == "discovery":
        with _spinner_view():
            render_data_discovery_page()
        return

    if section == "publish":
        with _spinner_view():
            publish.render_publish_page()
        return

    if section == "settings":
        with _spinner_view():
            settings.render_settings_page()
        return

    if section == "advanced_analytics":
        with _spinner_view():
            try:
                from app.views.analytics_advanced import render_analytics_advanced_page
                render_analytics_advanced_page()
            except ImportError:
                st.info("Advanced Analytics view is not yet available.")
        return

    if section == "data_catalog":
        with _spinner_view():
            try:
                from app.views.data_catalog import render_data_catalog_page
                render_data_catalog_page()
            except ImportError:
                st.info("Data Catalog view is not yet available.")
        return

    # ------------------------------------------------------------------ #
    # Data Workflows section (Socrata-backed)
    # ------------------------------------------------------------------ #
    view_key = wf_opts["view_key"]
    row_limit = wf_opts["row_limit"]
    show_ingest = wf_opts["show_ingest"]
    frames: dict = {}
    map_layers: dict = {}

    try:
        if show_ingest:
            frames = _load_all_frames(row_limit)
        else:
            frames = _load_workflow_frames(view_key, row_limit)
        if view_key == "spatial":
            map_layers = _load_map_layers(min(row_limit, 25_000))
        st.session_state["workflow_data_loaded"] = not frames_are_empty(frames)
    except ImportError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"Ingestion failed: {exc}")
        st.info("Set SOCRATA_APP_TOKEN in .env or use demo mode (Home → Load sample data).")
        render_empty_state(on_load_demo=lambda: os.environ.setdefault("MISSION_DEMO", "1"))
        st.stop()

    if frames_are_empty(frames):
        render_empty_state(on_load_demo=lambda: os.environ.setdefault("MISSION_DEMO", "1"))
        if st.button(t("go_workflows"), key="empty_to_workflows"):
            st.cache_data.clear()
            st.rerun()
        st.stop()

    results = _run_workflows(frames)
    roi = results["roi"]
    workflows.render_roi_header(roi)
    st.divider()

    if show_ingest:
        workflows.view_ingest(frames)
    elif view_key == "qa":
        workflows.view_qa(results)
    elif view_key == "spatial":
        workflows.view_spatial(results, map_layers)
    elif view_key == "contract":
        workflows.view_contract(results)
    elif view_key == "productivity":
        workflows.view_productivity(results)
    elif view_key == "quality":
        workflows.view_quality(results, frames)

    with st.expander("📊 ROI calculation detail", expanded=False):
        st.json(roi.as_dict())

    if not show_ingest and view_key != "quality":
        with st.expander("📥 Ingestion matrix", expanded=False):
            from app.data_loader import ingestion_summary
            summary = ingestion_summary(frames)
            st.dataframe(summary, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
