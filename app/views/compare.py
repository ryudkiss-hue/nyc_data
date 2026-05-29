"""Cross-dataset comparison — align two datasets and contrast them."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.ui import charts
from app.ui.components import empty_state, kpi_row, section_header


def _shared_columns(a: pd.DataFrame, b: pd.DataFrame) -> list[str]:
    return sorted(set(a.columns) & set(b.columns))


@st.fragment
def render_compare_tab() -> None:
    """Render the cross-dataset Compare tab."""
    section_header(
        "Compare Datasets",
        "Align two loaded datasets to contrast schemas, shared keys, and "
        "metric distributions side by side.",
        icon="🔀",
    )

    frames: dict = st.session_state.get("loaded_frames", {})
    frames = {k: v for k, v in frames.items() if v is not None and not v.empty}

    if len(frames) < 2:
        empty_state(
            "Need at least two datasets",
            "Load two or more datasets from the Home tab to use the comparison tools.",
            icon="🔀",
        )
        return

    keys = list(frames.keys())
    c1, c2 = st.columns(2)
    ds_a = c1.selectbox("Dataset A", keys, index=0, key="cmp_a")
    ds_b = c2.selectbox("Dataset B", keys, index=min(1, len(keys) - 1), key="cmp_b")
    if ds_a == ds_b:
        st.warning("Select two different datasets to compare.")
        return

    df_a, df_b = frames[ds_a], frames[ds_b]
    shared = _shared_columns(df_a, df_b)

    # ── Summary KPIs ──────────────────────────────────────────────────────
    kpi_row(
        [
            {"label": f"{ds_a} rows", "value": f"{len(df_a):,}", "icon": "🅰️"},
            {"label": f"{ds_b} rows", "value": f"{len(df_b):,}", "icon": "🅱️"},
            {"label": "Shared columns", "value": len(shared), "icon": "🔗"},
            {"label": "Row Δ", "value": f"{abs(len(df_a) - len(df_b)):,}", "icon": "±"},
        ]
    )
    st.divider()

    # ── Schema overlap ────────────────────────────────────────────────────
    st.subheader("Schema overlap")
    only_a = sorted(set(df_a.columns) - set(df_b.columns))
    only_b = sorted(set(df_b.columns) - set(df_a.columns))
    o1, o2, o3 = st.columns(3)
    with o1:
        st.caption(f"Only in **{ds_a}** ({len(only_a)})")
        st.dataframe(pd.DataFrame({"column": only_a}), use_container_width=True, hide_index=True, height=200)
    with o2:
        st.caption(f"Shared ({len(shared)})")
        st.dataframe(pd.DataFrame({"column": shared}), use_container_width=True, hide_index=True, height=200)
    with o3:
        st.caption(f"Only in **{ds_b}** ({len(only_b)})")
        st.dataframe(pd.DataFrame({"column": only_b}), use_container_width=True, hide_index=True, height=200)

    st.divider()

    # ── Metric distribution overlay ───────────────────────────────────────
    st.subheader("Distribution comparison")
    shared_numeric = [
        c for c in shared
        if pd.api.types.is_numeric_dtype(df_a[c]) and pd.api.types.is_numeric_dtype(df_b[c])
    ]
    if not shared_numeric:
        st.info("No shared numeric columns to compare distributions.")
        return

    metric = st.selectbox("Shared numeric column", shared_numeric, key="cmp_metric")
    combined = pd.concat(
        [
            pd.DataFrame({metric: df_a[metric].dropna(), "dataset": ds_a}),
            pd.DataFrame({metric: df_b[metric].dropna(), "dataset": ds_b}),
        ],
        ignore_index=True,
    )
    fig = charts.box_plot(combined, y=metric, group="dataset",
                          title=f"{metric} distribution: {ds_a} vs {ds_b}")
    summary = (
        combined.groupby("dataset")[metric]
        .agg(["count", "mean", "median", "std", "min", "max"])
        .round(2)
        .reset_index()
    )
    charts.render_with_table(
        fig, summary, caption="Box shows median/IQR; points are outliers.",
        table_label="View summary statistics", key="cmp_box",
    )
