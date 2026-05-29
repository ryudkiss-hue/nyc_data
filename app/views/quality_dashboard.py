"""Data quality dashboard tab for Manhattan Mission Control."""

from __future__ import annotations

import datetime
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from app.ui import charts
from app.ui.components import kpi_row, section_header
from socrata_toolkit.quality.profiler import DataType, ProfileGenerator


def _null_pct(df: pd.DataFrame) -> float:
    """Return null percentage (0-100) for a DataFrame."""
    total_cells = df.size
    if total_cells == 0:
        return 0.0
    return float(df.isna().sum().sum() / total_cells * 100)


def _dup_count(df: pd.DataFrame) -> int:
    """Return number of duplicate rows."""
    return int(df.duplicated().sum())


def _health_score(null_pct: float, dup_pct: float) -> float:
    """Compute health score 0-100."""
    return max(0.0, 100.0 - null_pct * 0.5 - dup_pct * 50.0)


def _health_color(score: float) -> str:
    if score >= 80:
        return "🟢"
    if score >= 50:
        return "🟡"
    return "🔴"


def _find_date_col(df: pd.DataFrame) -> str | None:
    """Return first column that looks like a date."""
    for col in df.columns:
        lc = col.lower()
        if "created_date" in lc or lc == "date":
            return col
    # Fall back to any datetime column
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col
    return None


def _days_ago(df: pd.DataFrame, date_col: str) -> int | None:
    """Return how many days ago the max value of date_col was."""
    try:
        series = pd.to_datetime(df[date_col], errors="coerce")
        max_dt = series.max()
        if pd.isna(max_dt):
            return None
        delta = datetime.datetime.now() - max_dt.to_pydatetime().replace(tzinfo=None)
        return int(delta.days)
    except Exception:  # noqa: BLE001
        return None


def _sla_badge(days: int | None) -> str:
    if days is None:
        return "⚪ Unknown"
    if days < 7:
        return f"🟢 {days}d ago"
    if days < 30:
        return f"🟡 {days}d ago"
    return f"🔴 {days}d ago"


def _anomaly_count(df: pd.DataFrame) -> int:
    """Count values > mean+3*std across all numeric columns."""
    count = 0
    for col in df.select_dtypes(include=[np.number]).columns:
        s = df[col].dropna()
        if len(s) < 2:
            continue
        threshold = s.mean() + 3 * s.std()
        count += int((s > threshold).sum())
    return count


def _build_quality_report(loaded_frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, df in loaded_frames.items():
        np_val = _null_pct(df)
        dup = _dup_count(df)
        dup_pct = dup / max(len(df), 1)
        score = _health_score(np_val, dup_pct)
        date_col = _find_date_col(df)
        last_record: str | None = None
        if date_col:
            days = _days_ago(df, date_col)
            last_record = f"{days}d ago" if days is not None else None
        rows.append(
            {
                "dataset": key,
                "health_score": round(score, 1),
                "null_pct": round(np_val, 2),
                "dup_count": dup,
                "row_count": len(df),
                "last_record_date": last_record or "",
            }
        )
    return pd.DataFrame(rows)


def render_quality_tab(loaded_frames: dict[str, pd.DataFrame]) -> None:
    """Render the data quality dashboard tab."""
    st.header("🔬 Data Quality Dashboard")

    if not loaded_frames:
        st.info(
            "No datasets are currently loaded. Use the sidebar to ingest datasets, "
            "then return here to view quality metrics."
        )
        return

    # ── Pre-compute per-dataset metrics ──────────────────────────────────────
    metrics: dict[str, dict[str, Any]] = {}
    for key, df in loaded_frames.items():
        np_val = _null_pct(df)
        dup = _dup_count(df)
        dup_pct = dup / max(len(df), 1)
        score = _health_score(np_val, dup_pct)
        metrics[key] = {
            "null_pct": np_val,
            "dup": dup,
            "dup_pct": dup_pct,
            "score": score,
        }

    total_nulls = sum(
        int(df.isna().sum().sum()) for df in loaded_frames.values()
    )
    total_dups = sum(m["dup"] for m in metrics.values())
    avg_health = float(np.mean([m["score"] for m in metrics.values()]))

    # ── 1. Overview metrics row ───────────────────────────────────────────────
    section_header("Overview", "Fleet-wide data quality at a glance", icon="📊")
    health_good = avg_health >= 70
    kpi_row(
        [
            {"label": "Datasets Loaded", "value": len(loaded_frames), "icon": "🗂️"},
            {"label": "Avg Health Score", "value": f"{avg_health:.0f}/100", "icon": "❤️",
             "delta": "healthy" if health_good else "needs review", "delta_good": health_good},
            {"label": "Total Null Cells", "value": f"{total_nulls:,}", "icon": "⬜"},
            {"label": "Duplicate Rows", "value": f"{total_dups:,}", "icon": "👥",
             "delta_good": total_dups == 0},
        ]
    )

    # Health-score bar chart with accessible table fallback
    if charts.available():
        health_df = pd.DataFrame(
            [{"dataset": k, "health": round(m["score"], 1)} for k, m in metrics.items()]
        ).sort_values("health")
        fig = charts.bar(
            health_df, x="health", y="dataset", title="Health score by dataset",
            orientation="h", height=max(220, 30 * len(health_df)),
        )
        charts.render_with_table(
            fig, health_df.rename(columns={"dataset": "Dataset", "health": "Health"}),
            caption="Lower bars indicate datasets needing attention.",
            table_label="View health scores as table", key="qd_health_chart",
        )

    st.divider()

    # ── 2. Per-dataset quality cards ─────────────────────────────────────────
    st.subheader("Per-Dataset Quality Cards")
    with st.expander("Expand dataset cards", expanded=True):
        for key, df in loaded_frames.items():
            m = metrics[key]
            score = m["score"]
            np_val = m["null_pct"]
            dup = m["dup"]

            with st.container(border=True):
                left, right = st.columns([3, 1])
                with left:
                    st.markdown(
                        f"**{key}** — {len(df):,} rows × {len(df.columns)} cols"
                    )
                with right:
                    st.markdown(
                        f"{_health_color(score)} Health: **{score:.1f}**"
                    )

                st.caption(f"Null density: {np_val:.1f}%")
                st.progress(min(np_val / 100, 1.0))

                # Top 5 columns by null %
                null_series = df.isna().mean() * 100
                top_nulls = (
                    null_series[null_series > 0]
                    .sort_values(ascending=False)
                    .head(5)
                    .reset_index()
                )
                top_nulls.columns = pd.Index(["Column", "Null %"])
                top_nulls["Null %"] = top_nulls["Null %"].round(2)
                if not top_nulls.empty:
                    st.markdown("**Top columns by null %**")
                    st.dataframe(top_nulls, use_container_width=False, hide_index=True)
                else:
                    st.success("No null values detected.")

                st.caption(f"Duplicate rows: {dup:,}")

    st.divider()

    # ── 3. Column profiling ───────────────────────────────────────────────────
    st.subheader("Column Profiling")
    profile_key = st.selectbox(
        "Select dataset to profile",
        options=list(loaded_frames.keys()),
        key="qd_profile_sel",
    )
    if profile_key:
        df_prof = loaded_frames[profile_key]
        with st.spinner("Profiling dataset…"):
            profiler = ProfileGenerator(sample_size=500)
            profile = profiler.profile_dataset(df_prof, table_name=profile_key)

        profile_rows: list[dict[str, Any]] = []
        for col_name, cp in profile.column_profiles.items():
            profile_rows.append(
                {
                    "Column": col_name,
                    "Type": (
                        cp.data_type.value
                        if isinstance(cp.data_type, DataType)
                        else str(cp.data_type)
                    ),
                    "Min": cp.min_value,
                    "Max": cp.max_value,
                    "Cardinality": cp.cardinality,
                }
            )
        profile_df = pd.DataFrame(profile_rows)
        st.dataframe(profile_df, use_container_width=True, hide_index=True)

    st.divider()

    # ── 4. SLA status panel ───────────────────────────────────────────────────
    st.subheader("Freshness SLA Status")
    sla_rows: list[dict[str, Any]] = []
    for key, df in loaded_frames.items():
        date_col = _find_date_col(df)
        if date_col:
            days = _days_ago(df, date_col)
            badge = _sla_badge(days)
        else:
            badge = "⚪ No date column"
        sla_rows.append(
            {"Dataset": key, "Date Column": date_col or "—", "Freshness": badge}
        )

    sla_df = pd.DataFrame(sla_rows)
    st.dataframe(sla_df, use_container_width=True, hide_index=True)

    st.divider()

    # ── 5. Anomaly summary ────────────────────────────────────────────────────
    st.subheader("Anomaly Summary (>mean+3σ)")
    anomaly_rows: list[dict[str, Any]] = []
    for key, df in loaded_frames.items():
        count = _anomaly_count(df)
        anomaly_rows.append({"Dataset": key, "Potential Outlier Values": count})

    anomaly_df = pd.DataFrame(anomaly_rows)
    st.dataframe(anomaly_df, use_container_width=True, hide_index=True)

    st.divider()

    # ── 6. Export quality report ──────────────────────────────────────────────
    st.subheader("Export Quality Report")
    report_df = _build_quality_report(loaded_frames)
    csv_bytes = report_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download Quality Report (CSV)",
        data=csv_bytes,
        file_name="quality_report.csv",
        mime="text/csv",
    )
