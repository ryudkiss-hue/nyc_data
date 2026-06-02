"""NYC DOT SIM Analyst Toolkit — Streamlit desktop application."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from datetime import date, timedelta
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
from socrata_toolkit.analysis.changepoint import detect_cusum_changepoint

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

_BOROUGH_OPTIONS = ["Manhattan", "Brooklyn", "Queens", "The Bronx", "Staten Island"]
_STATUS_OPTIONS = ["Open", "In Progress", "Closed", "Pending Review"]


# ---------------------------------------------------------------------------
# Fragment-wrapped chart sections
# ---------------------------------------------------------------------------

def _make_roi_chart_fragment():
    """Return an @st.fragment-decorated ROI chart renderer (or plain fn)."""

    def _render_roi_chart_inner(roi: object) -> None:
        """Render ROI header and JSON detail without triggering full-page reload."""
        workflows.render_roi_header(roi)
        with st.expander("📊 ROI calculation detail", expanded=False):
            st.json(roi.as_dict())

    if hasattr(st, "fragment"):
        return st.fragment(_render_roi_chart_inner)
    return _render_roi_chart_inner


def _make_ingestion_matrix_fragment():
    """Return an @st.fragment-decorated ingestion matrix renderer (or plain fn)."""

    def _render_ingestion_matrix_inner(frames: dict) -> None:
        """Render ingestion summary without triggering full-page reload."""
        with st.expander("📥 Ingestion matrix", expanded=False):
            from app.data_loader import ingestion_summary

            summary = ingestion_summary(frames)
            st.dataframe(summary, use_container_width=True, hide_index=True)

    if hasattr(st, "fragment"):
        return st.fragment(_render_ingestion_matrix_inner)
    return _render_ingestion_matrix_inner


# Build fragment callables once at module level
_render_roi_chart = _make_roi_chart_fragment()
_render_ingestion_matrix = _make_ingestion_matrix_fragment()


# ---------------------------------------------------------------------------
# Cached data loaders
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Anomaly detection helpers
# ---------------------------------------------------------------------------

_ANOMALY_CANDIDATE_KEYS = ("df", "data", "workflow_df", "sample_df")
_CUSUM_SIGMA_THRESHOLD = 3.0  # flag anomaly when peak CUSUM > 3 × std


@st.cache_data(ttl=300)
def _detect_sidebar_anomaly(series_values: tuple[float, ...]) -> bool:
    """Return True if the CUSUM statistic indicates a real level-shift.

    Uses a threshold of ``_CUSUM_SIGMA_THRESHOLD`` standard deviations: the
    peak absolute CUSUM value must exceed ``k * std(series)`` to be flagged.
    This avoids false positives on flat or low-variance data where
    ``detect_cusum_changepoint`` always returns a (trivially maximal) index.

    Accepts a tuple (hashable) so that ``@st.cache_data`` can hash the input.
    """
    import pandas as pd

    series = pd.Series(series_values)
    if len(series) < 10:
        return False
    sigma = float(series.std())
    if sigma == 0:
        return False
    mu = float(series.mean())
    cusum = (series - mu).cumsum()
    return float(cusum.abs().max()) > _CUSUM_SIGMA_THRESHOLD * sigma


def _maybe_render_anomaly_badge() -> None:
    """Render a sidebar warning badge if CUSUM detects a changepoint.

    Tries session-state keys in order: ``_ANOMALY_CANDIDATE_KEYS``.  Uses the
    first DataFrame found with at least 10 rows.  Silently skips when no data
    is loaded.
    """
    try:
        import pandas as pd

        frame: pd.DataFrame | None = None
        for key in _ANOMALY_CANDIDATE_KEYS:
            candidate = st.session_state.get(key)
            if isinstance(candidate, pd.DataFrame) and len(candidate) >= 10:
                frame = candidate
                break

        if frame is None:
            return

        numeric_cols = frame.select_dtypes(include="number").columns
        if len(numeric_cols) == 0:
            return

        series = frame[numeric_cols[0]].dropna()
        if len(series) < 10:
            return

        if _detect_sidebar_anomaly(tuple(series.tolist())):
            st.sidebar.warning(
                "⚠️ Anomaly detected in data — check CUSUM chart in Advanced Analytics"
            )
    except Exception:  # noqa: BLE001
        pass  # Never crash the sidebar


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def _init_filter_defaults() -> None:
    """Initialise sticky sidebar filter state with safe defaults."""
    if "filter_borough" not in st.session_state:
        st.session_state["filter_borough"] = []
    if "filter_date_range" not in st.session_state:
        today = date.today()
        st.session_state["filter_date_range"] = (today - timedelta(days=90), today)
    if "filter_status" not in st.session_state:
        st.session_state["filter_status"] = []


def _render_sticky_filters(section: str) -> None:
    """Render persistent data filters in the sidebar."""
    with st.expander("🔽 Data Filters", expanded=False):
        st.session_state["filter_borough"] = st.multiselect(
            "Borough",
            _BOROUGH_OPTIONS,
            default=st.session_state.get("filter_borough", []),
            key="sb_filter_borough",
            placeholder="All boroughs",
        )

        default_range = st.session_state.get(
            "filter_date_range",
            (date.today() - timedelta(days=90), date.today()),
        )
        st.session_state["filter_date_range"] = st.date_input(
            "Date range",
            value=default_range,
            key="sb_filter_date_range",
        )

        st.session_state["filter_status"] = st.multiselect(
            "Status",
            _STATUS_OPTIONS,
            default=st.session_state.get("filter_status", []),
            key="sb_filter_status",
            placeholder="All statuses",
        )

        active_filters = sum([
            1 if st.session_state["filter_borough"] else 0,
            1 if st.session_state["filter_status"] else 0,
        ])
        if active_filters:
            st.caption(f"✅ {active_filters} filter(s) active")
            if st.button("Clear filters", key="sb_clear_filters", use_container_width=True):
                st.session_state["filter_borough"] = []
                st.session_state["filter_date_range"] = (
                    date.today() - timedelta(days=90),
                    date.today(),
                )
                st.session_state["filter_status"] = []
                st.rerun()


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

        # Anomaly badge — shown when a changepoint is detected in loaded data
        _maybe_render_anomaly_badge()

        # Sticky filter bar
        _render_sticky_filters(section)
        st.divider()

        wf_opts: dict = {"view_key": "qa", "row_limit": 10_000, "show_ingest": False}

        if section == "workflows":
            wf_labels = list(WORKFLOW_KEYS.values())
            view_label = st.radio("Workflow", wf_labels, index=0, key="wf_select")
            wf_opts["view_key"] = [k for k, v in WORKFLOW_KEYS.items() if v == view_label][0]
            wf_opts["row_limit"] = st.slider(
                "Max rows / dataset", 1_000, 50_000, 10_000, step=1_000
            )
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

    # Initialise persistent filter state defaults
    _init_filter_defaults()

    # Persistent filter state (legacy key kept for compatibility)
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
        with st.status("Loading data from Socrata…", expanded=True) as _status:
            if show_ingest:
                _status.update(label="Loading full ingestion matrix from Socrata…")
                frames = _load_all_frames(row_limit)
            else:
                _status.update(
                    label=f"Loading '{WORKFLOW_KEYS.get(view_key, view_key)}' datasets from Socrata…"
                )
                frames = _load_workflow_frames(view_key, row_limit)
            if view_key == "spatial":
                _status.update(label="Loading Manhattan map layers…")
                map_layers = _load_map_layers(min(row_limit, 25_000))
            dataset_count = len([k for k, v in frames.items() if not getattr(v, "empty", True)])
            _status.update(
                label=f"Loaded {dataset_count} dataset(s) — ready",
                state="complete",
                expanded=False,
            )
        st.session_state["workflow_data_loaded"] = not frames_are_empty(frames)
    except ImportError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"Ingestion failed: {exc}")
        st.info("Set SOCRATA_APP_TOKEN in your .env file to authenticate with Socrata.")
        render_empty_state()
        st.stop()

    if frames_are_empty(frames):
        render_empty_state()
        if st.button(t("go_workflows"), key="empty_to_workflows"):
            st.cache_data.clear()
            st.rerun()
        st.stop()

    results = _run_workflows(frames)
    roi = results["roi"]

    # Fragment-wrapped ROI header + detail (rerenders without full-page reload)
    _render_roi_chart(roi)
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

    if not show_ingest and view_key != "quality":
        # Fragment-wrapped ingestion matrix (rerenders independently)
        _render_ingestion_matrix(frames)


if __name__ == "__main__":
    main()
