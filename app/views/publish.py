"""Publish & analyst pack operations."""

from __future__ import annotations

import streamlit as st

from app.services import agency
from app.utils.i18n import t
from app.utils.report_export import build_excel_report, build_pdf_report


def render_publish_page() -> None:
    st.subheader(t("publish_title"))
    st.caption(t("publish_caption"))

    root = agency.repo_root()
    analyst_prof = root / "config" / "analyst_profile.yaml"
    if not analyst_prof.exists():
        analyst_prof = root / "config" / "analyst_profile.example.yaml"

    publish_prof = root / "config" / "publish_profile.yaml"
    if not publish_prof.exists():
        publish_prof = root / "config" / "publish_profile.example.yaml"

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Analyst profile**")
        st.code(str(analyst_prof), language=None)
        offline = st.checkbox(t("offline_pack"), value=False)
        if st.button(t("run_pack"), type="primary", key="run_pack"):
            with st.spinner("Running analyst pack…"):
                try:
                    out = agency.run_analyst_pack(profile_path=analyst_prof, offline=offline)
                    st.session_state["last_pack"] = out
                    st.success(f"Pack written: {out['pack_dir']}")
                    if out.get("warnings"):
                        for w in out["warnings"]:
                            st.warning(w)
                except Exception as exc:
                    st.error(str(exc))

    with col2:
        st.markdown("**Publish profile**")
        st.code(str(publish_prof), language=None)
        packs = agency.list_pack_dirs()
        pack_labels = [p.name for p in packs] or ["(no packs yet)"]
        selected = st.selectbox("Pack folder", pack_labels, index=0 if packs else 0)
        pack_dir = packs[pack_labels.index(selected)] if packs and selected in pack_labels else None
        dry_run = st.checkbox(t("dry_run"), value=True)
        if st.button(t("publish_pack_btn"), key="publish_pack") and pack_dir:
            with st.spinner("Publishing…"):
                try:
                    report = agency.publish_pack_ui(
                        pack_dir=pack_dir,
                        profile_path=publish_prof,
                        dry_run=dry_run,
                    )
                    st.session_state["last_publish"] = report
                    for action in report.get("actions", []):
                        icon = "✅" if action.get("ok") else "❌"
                        st.markdown(f"{icon} **{action.get('kind')}** — {action.get('detail')}")
                except Exception as exc:
                    st.error(str(exc))

    if "last_pack" in st.session_state:
        with st.expander("Last pack run", expanded=False):
            st.json(st.session_state["last_pack"])

    latest = agency.latest_pack_dir()
    if latest and latest.exists():
        st.markdown("**Latest pack artifacts**")
        files = sorted([p.name for p in latest.iterdir() if p.is_file()])[:20]
        st.write(", ".join(files) if files else "(empty)")

    # ------------------------------------------------------------------ #
    # Export Report                                                        #
    # ------------------------------------------------------------------ #
    with st.expander("Export Report", expanded=False):
        st.caption("Download a snapshot of the current pack data as Excel or PDF.")

        # Build report sections from session state when available.
        # Sample borough data is only included when no real pack has been run.
        last_pack: dict = st.session_state.get("last_pack", {})
        warnings = last_pack.get("warnings", [])
        report_sections: dict[str, list[dict]] = {
            "Pack Summary": [
                {
                    "Pack directory": last_pack.get("pack_dir", "(none)"),
                    "Datasets": last_pack.get("dataset_count", "—"),
                    "Generated": last_pack.get("generated_at", "—"),
                }
            ],
            "Warnings": [{"Warning": w} for w in warnings] if warnings else [{"Warning": "(none)"}],
        }
        if not last_pack:
            report_sections["Demo: Borough Snapshot"] = [
                {"Borough": "Manhattan", "Open": 42, "Closed": 118},
                {"Borough": "Brooklyn", "Open": 37, "Closed": 95},
                {"Borough": "Queens", "Open": 29, "Closed": 74},
                {"Borough": "Bronx", "Open": 18, "Closed": 52},
                {"Borough": "Staten Island", "Open": 6, "Closed": 21},
            ]

        # Generate bytes lazily — only when analyst clicks "Prepare Export".
        # Bytes are cached in session_state so download buttons work immediately
        # without rebuilding the workbook on every Streamlit rerender.
        if st.button("Prepare Export", key="prepare_export"):
            st.session_state["_export_excel"] = build_excel_report("SIM Inspection Report", report_sections)
            st.session_state["_export_pdf"] = build_pdf_report("SIM Inspection Report", report_sections)

        if "_export_excel" in st.session_state:
            st.download_button(
                label="Download Excel (.xlsx)",
                data=st.session_state["_export_excel"],
                file_name="sim_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_excel",
            )

        if st.session_state.get("_export_pdf") is not None:
            st.download_button(
                label="Download PDF",
                data=st.session_state["_export_pdf"],
                file_name="sim_report.pdf",
                mime="application/pdf",
                key="dl_pdf",
            )
        elif "_export_excel" in st.session_state:
            st.info(
                "PDF export requires WeasyPrint — included in `pip install -e '.[mission]'`."
            )
