"""Export Center — one place to download loaded datasets in any format."""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from app.ui.components import empty_state, kpi_row, section_header
from app.utils import export


@st.fragment
def render_export_center() -> None:
    """Render the Export Center tab.

    Wrapped in @st.fragment so format/dataset selection reruns only this tab,
    not the entire 11-tab app — important on slower connections.
    """
    section_header(
        "Export Center",
        "Download loaded datasets as CSV, Excel, JSON, or a bundled ZIP archive.",
        icon="📦",
    )

    frames: dict = st.session_state.get("loaded_frames", {})
    frames = {k: v for k, v in frames.items() if v is not None and not v.empty}

    if not frames:
        empty_state(
            "No datasets loaded",
            "Load data from the Home tab or run the Apex Pipeline, then return here to export.",
            icon="📦",
        )
        return

    total_rows = sum(len(df) for df in frames.values())
    total_cols = sum(len(df.columns) for df in frames.values())
    kpi_row(
        [
            {"label": "Datasets", "value": len(frames), "icon": "🗂️"},
            {"label": "Total Rows", "value": f"{total_rows:,}", "icon": "📊"},
            {"label": "Total Columns", "value": f"{total_cols:,}", "icon": "📋"},
        ]
    )
    st.divider()

    # Dataset summary
    st.dataframe(export.summary_table(frames), use_container_width=True, hide_index=True)
    st.divider()

    # ── Single dataset export ────────────────────────────────────────────
    st.subheader("Single dataset")
    c1, c2 = st.columns([2, 1])
    selected = c1.selectbox("Dataset", list(frames.keys()), key="export_single_ds")
    fmt = c2.selectbox("Format", ["CSV", "JSON"], key="export_single_fmt")
    df = frames[selected]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    if fmt == "CSV":
        st.download_button(
            "⬇ Download CSV",
            export.to_csv_bytes(df),
            file_name=f"{selected}_{ts}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.download_button(
            "⬇ Download JSON",
            export.to_json_bytes(df),
            file_name=f"{selected}_{ts}.json",
            mime="application/json",
            use_container_width=True,
        )

    st.divider()

    # ── Bulk export ──────────────────────────────────────────────────────
    st.subheader("Bulk export")
    chosen = st.multiselect(
        "Datasets to include",
        list(frames.keys()),
        default=list(frames.keys()),
        key="export_bulk_ds",
    )
    bundle = {k: frames[k] for k in chosen}
    b1, b2, b3 = st.columns(3)

    with b1:
        st.download_button(
            "⬇ ZIP (CSV)",
            export.to_zip_bundle(bundle, fmt="csv") if bundle else b"",
            file_name=f"mission_control_export_{ts}.zip",
            mime="application/zip",
            disabled=not bundle,
            use_container_width=True,
        )
    with b2:
        st.download_button(
            "⬇ ZIP (JSON)",
            export.to_zip_bundle(bundle, fmt="json") if bundle else b"",
            file_name=f"mission_control_export_json_{ts}.zip",
            mime="application/zip",
            disabled=not bundle,
            use_container_width=True,
        )
    with b3:
        xlsx = export.to_excel_bytes(bundle) if bundle else None
        if xlsx is not None:
            st.download_button(
                "⬇ Excel (multi-sheet)",
                xlsx,
                file_name=f"mission_control_export_{ts}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        else:
            st.button("Excel unavailable", disabled=True, use_container_width=True,
                      help="Install xlsxwriter or openpyxl for Excel export.")
