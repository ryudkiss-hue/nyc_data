"""Manhattan Mission Control — agency-grade Streamlit application."""

from __future__ import annotations

import streamlit as st

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
from app.ui.theme import inject_theme, render_agency_header, render_skip_link
from app.views import home, publish, settings, workflows

st.set_page_config(
    page_title="Manhattan Mission Control | NYC DOT SIM",
    page_icon="🚧",
    layout="wide",
    initial_sidebar_state="expanded",
)

WORKFLOW_VIEWS = {
    "QA/QC & Inventory Ledger": "qa",
    "Spatial Conflict Detection": "spatial",
    "Contract & Dispatch Clearance": "contract",
    "Productivity & ADA Progress": "productivity",
}

NAV_PAGES = ["Home", "Analyst Workflows", "Publish & Pack", "Settings & Quality"]


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Loading workflow datasets…")
def _load_workflow_frames(workflow_key: str, limit: int) -> dict:
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


def main() -> None:
    inject_theme()
    render_skip_link()

    with st.sidebar:
        st.markdown("**NYC DOT · SIM**")
        page = st.radio("Navigation", NAV_PAGES, label_visibility="collapsed")
        st.divider()
        view_key = "qa"
        view_label = WORKFLOW_VIEWS["QA/QC & Inventory Ledger"]
        show_ingest = False
        row_limit = 10_000

        if page == "Analyst Workflows":
            view_label = st.radio("Workflow", list(WORKFLOW_VIEWS.keys()), index=0)
            view_key = WORKFLOW_VIEWS[view_label]
            row_limit = st.slider("Max rows per dataset", 1_000, 50_000, 10_000, step=1_000)
            if demo_mode_enabled():
                st.info("Demo mode — no live API.")
            if st.button("Refresh cache", type="primary"):
                st.cache_data.clear()
            st.caption(f"Loads {len(WORKFLOW_DATASETS.get(view_key, ()))} datasets for this view.")
            show_ingest = st.checkbox("Show full ingestion matrix")

        if st.button("Clear session", help="Reset onboarding and cached UI state"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.cache_data.clear()
            st.rerun()

    token = token_status()
    render_agency_header(
        demo=bool(token.get("demo_mode")),
        live_auth=bool(token["configured"] or token.get("key_pair")),
    )

    if page == "Home":
        home.render_home_page()
        return

    if page == "Publish & Pack":
        publish.render_publish_page()
        return

    if page == "Settings & Quality":
        settings.render_settings_page()
        return

    # Analyst Workflows
    frames = {}
    map_layers = {}
    results = None
    roi = None
    try:
        if show_ingest:
            frames = _load_all_frames(row_limit)
        else:
            frames = _load_workflow_frames(view_key, row_limit)
        if view_key == "spatial":
            map_layers = _load_map_layers(min(row_limit, 25_000))
        results = _run_workflows(frames)
        roi = results["roi"]
    except ImportError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"Ingestion failed: {exc}")
        st.info('Set SOCRATA_APP_TOKEN in .env or run with MISSION_DEMO=1')
        st.stop()

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

    if roi is not None:
        with st.expander("ROI calculation detail"):
            st.json(roi.as_dict())


if __name__ == "__main__":
    main()
