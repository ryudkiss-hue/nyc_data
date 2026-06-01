"""Data Catalog view — dataset registry, freshness checks, API usage dashboard,
and global search across all registered Socrata datasets."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import streamlit as st

from app.data_loader import DATASET_REGISTRY, demo_mode_enabled

try:
    import plotly.express as px

    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import requests as _requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

logger = logging.getLogger(__name__)

DOMAIN = "data.cityofnewyork.us"

# ---------------------------------------------------------------------------
# SQLite API log helpers (item 96)
# ---------------------------------------------------------------------------


def log_api_call(key: str, rows: int, status: str, duration_ms: int) -> None:
    import sqlite3

    db = Path("data/api_log.db")
    db.parent.mkdir(exist_ok=True)
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS api_calls"
            "(ts TEXT, dataset_key TEXT, rows_fetched INT, status TEXT, duration_ms INT)"
        )
        conn.execute(
            "INSERT INTO api_calls VALUES (?,?,?,?,?)",
            (pd.Timestamp.now().isoformat(), key, rows, status, duration_ms),
        )
        conn.commit()


def load_api_log() -> pd.DataFrame:
    import sqlite3

    db = Path("data/api_log.db")
    if not db.exists():
        return pd.DataFrame(columns=["ts", "dataset_key", "rows_fetched", "status", "duration_ms"])
    with sqlite3.connect(db) as conn:
        return pd.read_sql("SELECT * FROM api_calls ORDER BY ts DESC LIMIT 1000", conn)


# ---------------------------------------------------------------------------
# Freshness check helpers (item 94)
# ---------------------------------------------------------------------------


@st.cache_data(ttl=86_400, show_spinner=False)
def _fetch_last_updated(fourfour: str) -> str | None:
    """Fetch the most recent :updated_at timestamp for a Socrata dataset."""
    if not HAS_REQUESTS:
        return None
    url = f"https://{DOMAIN}/resource/{fourfour}.json"
    params = {"$select": ":updated_at", "$limit": 1, "$order": ":updated_at DESC"}
    try:
        resp = _requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        rows = resp.json()
        if rows and ":updated_at" in rows[0]:
            return rows[0][":updated_at"]
    except Exception as exc:
        logger.debug("_fetch_last_updated failed for %s: %s", fourfour, exc)
    return None


@st.cache_data(ttl=86_400, show_spinner=False)
def _fetch_row_count(fourfour: str) -> int | None:
    """Fetch the approximate row count for a Socrata dataset."""
    if not HAS_REQUESTS:
        return None
    url = f"https://{DOMAIN}/resource/{fourfour}.json"
    params = {"$select": "count(*) as n", "$limit": 1}
    try:
        resp = _requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        rows = resp.json()
        if rows and "n" in rows[0]:
            return int(rows[0]["n"])
    except Exception as exc:
        logger.debug("_fetch_row_count failed for %s: %s", fourfour, exc)
    return None


def _freshness_badge(days: int | None) -> str:
    if days is None:
        return "⚪ Unknown"
    if days < 7:
        return "🟢 Fresh"
    if days <= 30:
        return "🟡 Aging"
    return "🔴 Stale"


# ---------------------------------------------------------------------------
# Global search helper (item 87)
# ---------------------------------------------------------------------------


@st.cache_data(ttl=86_400, show_spinner=False)
def _search_dataset(key: str, q: str, limit: int = 20) -> pd.DataFrame:
    """Run a $q= full-text search on a single dataset."""
    try:
        meta = DATASET_REGISTRY[key]
        if not HAS_REQUESTS:
            return pd.DataFrame()
        url = f"https://{DOMAIN}/resource/{meta['fourfour']}.json"
        params = {"$q": q, "$limit": limit}
        resp = _requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        df.insert(0, "source_dataset", key)
        return df
    except Exception as exc:
        logger.debug("_search_dataset failed for %s: %s", key, exc)
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _render_catalog_table() -> None:
    """Item 95 — Data Catalog table."""
    st.subheader("Dataset Registry")

    rows = []
    for key, meta in DATASET_REGISTRY.items():
        fourfour = meta.get("fourfour", "")
        rows.append(
            {
                "key": key,
                "label": meta.get("label", ""),
                "group": meta.get("group", ""),
                "fourfour": fourfour,
                "socrata_url": f"https://{DOMAIN}/resource/{fourfour}.json" if fourfour else "",
                "default_where": meta.get("default_where", ""),
            }
        )
    catalog_df = pd.DataFrame(rows)

    # Filter by group
    all_groups = sorted(catalog_df["group"].unique().tolist())
    selected_groups = st.multiselect(
        "Filter by group",
        options=all_groups,
        default=all_groups,
        key="catalog_group_filter",
    )
    filtered = catalog_df[catalog_df["group"].isin(selected_groups)]

    st.dataframe(filtered, use_container_width=True)

    # Click-to-copy fourfour
    st.subheader("Dataset Identifiers (fourfour)")
    for _, row in filtered.iterrows():
        with st.expander(f"{row['label']} — {row['key']}"):
            st.code(row["fourfour"], language=None)
            if row["socrata_url"]:
                st.markdown(f"[Open on NYC Open Data]({row['socrata_url']})")


def _render_freshness_check() -> None:
    """Item 94 — Dataset Freshness check."""
    st.subheader("Dataset Freshness")
    st.caption("Check when each dataset was last updated on Socrata.")

    if not HAS_REQUESTS:
        st.warning("Install `requests` to enable freshness checks (`pip install requests`).")
        return

    if not st.button("Check Dataset Freshness", key="freshness_btn"):
        st.info("Click the button above to check freshness for all registered datasets.")
        return

    results = []
    progress = st.progress(0.0, text="Checking datasets…")
    keys = list(DATASET_REGISTRY.keys())

    for i, key in enumerate(keys):
        meta = DATASET_REGISTRY[key]
        fourfour = meta.get("fourfour", "")
        last_updated_str = _fetch_last_updated(fourfour) if fourfour else None
        row_count = _fetch_row_count(fourfour) if fourfour else None

        days_since: int | None = None
        if last_updated_str:
            try:
                last_ts = pd.Timestamp(last_updated_str)
                if last_ts.tzinfo is not None:
                    last_ts = last_ts.tz_localize(None)
                days_since = (pd.Timestamp.now() - last_ts).days
            except Exception:
                pass

        results.append(
            {
                "key": key,
                "label": meta.get("label", ""),
                "fourfour": fourfour,
                "last_updated": last_updated_str or "—",
                "days_since_update": days_since if days_since is not None else "—",
                "row_count": row_count if row_count is not None else "—",
                "freshness": _freshness_badge(days_since),
            }
        )
        progress.progress((i + 1) / len(keys), text=f"Checked {i + 1}/{len(keys)}")

    progress.empty()
    freshness_df = pd.DataFrame(results)
    st.dataframe(freshness_df, use_container_width=True)


def _render_api_usage() -> None:
    """Item 96 — API Usage Dashboard."""
    st.subheader("API Usage Dashboard")
    st.caption("Tracks calls logged via `log_api_call()` to `data/api_log.db`.")

    try:
        log_df = load_api_log()
    except Exception as exc:
        st.warning(f"Could not load API log: {exc}")
        return

    if log_df.empty:
        st.info("No API calls logged yet. The log is populated as datasets are fetched.")
        return

    log_df["ts"] = pd.to_datetime(log_df["ts"], errors="coerce")
    log_df = log_df.dropna(subset=["ts"])
    log_df["date"] = log_df["ts"].dt.date

    today = pd.Timestamp.now().date()
    week_ago = today - pd.Timedelta(days=7)

    calls_today = int((log_df["date"] == today).sum())
    calls_week = int((log_df["date"] >= week_ago).sum())
    errors_429 = int(log_df["status"].astype(str).str.contains("429").sum())

    # Estimate bytes saved: assume avg 500 bytes/row JSON vs 100 bytes/row parquet
    total_rows_cached = int(log_df["rows_fetched"].sum())
    bytes_saved_mb = round(total_rows_cached * (500 - 100) / 1_048_576, 2)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Calls today", f"{calls_today:,}")
    c2.metric("Calls this week", f"{calls_week:,}")
    c3.metric("Est. bytes saved by cache", f"{bytes_saved_mb:.1f} MB")
    c4.metric("Rate-limit events (429)", f"{errors_429:,}")

    st.subheader("Calls per Dataset per Day")
    if not HAS_PLOTLY:
        st.info("Install plotly for the API usage chart.")
        return

    calls_by_day_dataset = (
        log_df.groupby(["date", "dataset_key"])
        .size()
        .reset_index(name="call_count")
    )
    calls_by_day_dataset["date"] = calls_by_day_dataset["date"].astype(str)

    fig = px.bar(
        calls_by_day_dataset,
        x="date",
        y="call_count",
        color="dataset_key",
        title="API Calls per Dataset per Day",
        labels={"date": "Date", "call_count": "Calls", "dataset_key": "Dataset"},
        barmode="stack",
    )
    fig.update_layout(height=400, margin={"t": 40, "b": 20})
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Raw API log (last 100 entries)"):
        st.dataframe(log_df.head(100), use_container_width=True)


def _render_global_search() -> None:
    """Item 87 — Global Search across all datasets."""
    st.subheader("Global Search")
    st.caption("Search across all registered datasets using Socrata full-text search ($q=).")

    search_term = st.text_input(
        "Search across all datasets (runs $q= on each)",
        placeholder="e.g. MANHATTAN, sidewalk, open permit…",
        key="global_search_input",
    )

    if not search_term or not search_term.strip():
        return

    if not HAS_REQUESTS:
        st.warning("Install `requests` to enable global search (`pip install requests`).")
        return

    if demo_mode_enabled():
        st.warning("Global search requires live Socrata access. Demo mode is active.")
        return

    term = search_term.strip()
    all_keys = list(DATASET_REGISTRY.keys())

    results_list: list[pd.DataFrame] = []
    counts: dict[str, int] = {}

    progress = st.progress(0.0, text=f"Searching '{term}' across {len(all_keys)} datasets…")
    for i, key in enumerate(all_keys):
        df = _search_dataset(key, term, limit=20)
        if not df.empty:
            results_list.append(df)
            counts[key] = len(df)
        else:
            counts[key] = 0
        progress.progress(
            (i + 1) / len(all_keys), text=f"Searched {i + 1}/{len(all_keys)} datasets"
        )

    progress.empty()

    # Result counts per dataset
    counts_df = (
        pd.DataFrame(list(counts.items()), columns=["dataset_key", "results"])
        .sort_values("results", ascending=False)
    )
    st.subheader("Results per Dataset")
    st.dataframe(counts_df[counts_df["results"] > 0], use_container_width=True)

    if results_list:
        combined = pd.concat(results_list, ignore_index=True)
        st.subheader(
            f"Combined Results ({len(combined):,} rows across {len(results_list)} datasets)"
        )
        st.dataframe(combined, use_container_width=True)

        csv_bytes = combined.to_csv(index=False).encode()
        st.download_button(
            label="Download search results CSV",
            data=csv_bytes,
            file_name=f"search_{term.replace(' ', '_')}.csv",
            mime="text/csv",
        )
    else:
        st.info(f"No results found for '{term}' across any registered dataset.")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def render_data_catalog_page() -> None:
    """Render the Data Catalog page."""
    st.title("Data Catalog")
    st.caption(
        "Browse all registered NYC Open Data datasets, check freshness, monitor API usage, "
        "and run cross-dataset full-text searches."
    )

    # --- Global Search at the top (item 87) ---
    with st.container():
        _render_global_search()

    st.divider()

    tab_catalog, tab_freshness, tab_api = st.tabs([
        "📚 Dataset Registry",
        "🕐 Dataset Freshness",
        "📊 API Usage",
    ])

    with tab_catalog:
        _render_catalog_table()

    with tab_freshness:
        _render_freshness_check()

    with tab_api:
        _render_api_usage()
