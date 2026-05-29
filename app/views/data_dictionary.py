"""Data Dictionary — searchable metadata browser for loaded datasets."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.ui.components import empty_state, kpi_row, section_header
from app.utils import annotations


def _infer_kind(series: pd.Series) -> str:
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    return "text"


def _profile_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Per-column metadata: type, null %, cardinality, sample."""
    rows = []
    n = len(df)
    for col in df.columns:
        s = df[col]
        nulls = int(s.isna().sum())
        sample = s.dropna().astype(str).head(3).tolist()
        rows.append(
            {
                "Column": col,
                "Type": _infer_kind(s),
                "Null %": round(100.0 * nulls / n, 1) if n else 0.0,
                "Unique": int(s.nunique(dropna=True)),
                "Sample": ", ".join(sample)[:80],
            }
        )
    return pd.DataFrame(rows)


@st.fragment
def render_data_dictionary() -> None:
    """Render the Data Dictionary tab.

    Wrapped in @st.fragment so search/select interactions rerun only this tab.
    """
    section_header(
        "Data Dictionary",
        "Searchable field-level metadata across every loaded dataset — types, "
        "null rates, cardinality, and sample values.",
        icon="📖",
    )

    frames: dict = st.session_state.get("loaded_frames", {})
    frames = {k: v for k, v in frames.items() if v is not None and not v.empty}

    if not frames:
        empty_state(
            "No datasets loaded",
            "Load data first, then browse its schema and field definitions here.",
            icon="📖",
        )
        return

    # Global field search
    query = st.text_input(
        "🔍 Search fields across all datasets",
        placeholder="e.g. bbl, latitude, borough, date…",
        key="dict_search",
    ).strip().lower()

    total_fields = sum(len(df.columns) for df in frames.values())
    kpi_row(
        [
            {"label": "Datasets", "value": len(frames), "icon": "🗂️"},
            {"label": "Total Fields", "value": total_fields, "icon": "🏷️"},
        ]
    )
    st.divider()

    if query:
        # Cross-dataset search results
        hits = []
        for name, df in frames.items():
            for col in df.columns:
                if query in col.lower():
                    hits.append({"Dataset": name, "Field": col, "Type": _infer_kind(df[col])})
        if hits:
            st.success(f"Found {len(hits)} matching field(s).")
            st.dataframe(pd.DataFrame(hits), use_container_width=True, hide_index=True)
        else:
            st.warning(f"No fields match “{query}”.")
        st.divider()

    # Per-dataset detail
    selected = st.selectbox("Inspect dataset", list(frames.keys()), key="dict_select")
    df = frames[selected]
    st.caption(f"{len(df):,} rows · {len(df.columns)} columns")
    profile = _profile_columns(df)
    st.dataframe(
        profile,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Null %": st.column_config.ProgressColumn(
                "Null %", min_value=0, max_value=100, format="%.1f%%"
            ),
        },
    )
    st.download_button(
        "⬇ Export schema (CSV)",
        profile.to_csv(index=False).encode("utf-8"),
        file_name=f"{selected}_schema.csv",
        mime="text/csv",
    )

    # ── Annotations ───────────────────────────────────────────────────────
    st.divider()
    note_n = annotations.count(selected)
    section_header(
        "Annotations",
        f"Capture institutional knowledge about “{selected}” — {note_n} note(s).",
        icon="📝",
    )
    with st.form(key=f"note_form_{selected}", clear_on_submit=True):
        note_text = st.text_area("Add a note", placeholder="e.g. BBL field is sparse before 2019…")
        fc1, fc2 = st.columns([1, 3])
        tag = fc1.text_input("Tag", placeholder="quality")
        submitted = fc2.form_submit_button("💾 Save note", use_container_width=True)
        if submitted and annotations.add_note(selected, note_text, tag=tag):
            st.rerun()

    notes = annotations.list_notes(selected)
    if notes:
        for i, n in enumerate(reversed(notes)):
            real_idx = len(notes) - 1 - i
            with st.container(border=True):
                meta = f"🏷️ {n['tag']} · " if n.get("tag") else ""
                st.markdown(f"{meta}*{n['timestamp']}* — {n['author']}")
                st.markdown(n["text"])
                if st.button("🗑 Delete", key=f"del_note_{selected}_{real_idx}"):
                    annotations.delete_note(selected, real_idx)
                    st.rerun()
        # Export
        ec1, ec2 = st.columns(2)
        ec1.download_button(
            "⬇ Notes (CSV)", annotations.export_csv(),
            file_name="annotations.csv", mime="text/csv", use_container_width=True,
        )
        ec2.download_button(
            "⬇ Notes (JSON)", annotations.export_json().encode("utf-8"),
            file_name="annotations.json", mime="application/json", use_container_width=True,
        )
