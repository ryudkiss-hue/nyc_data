"""Settings, readiness, completeness, health."""

from __future__ import annotations

import streamlit as st

from app.services import agency
from app.ui.theme import render_readiness_bars
from app.utils.i18n import t
from socrata_toolkit.core.readiness import run_readiness_checks


def render_settings_page() -> None:
    st.subheader(t("settings_title"))

    tab_ready, tab_complete, tab_health, tab_logs = st.tabs(
        [t("tab_readiness"), t("tab_completeness"), t("tab_health"), t("tab_logs")]
    )

    with tab_ready:
        report = run_readiness_checks()
        st.metric("Overall readiness", f"{report['overall_score']:.1f}%")
        render_readiness_bars(report.get("axis_scores", {}))
        st.caption(report.get("note", ""))
        with st.expander("Failed checks"):
            for axis, items in report.get("axes", {}).items():
                failed = [i for i in items if not i.get("ok")]
                if failed:
                    st.markdown(f"**{axis}**")
                    for item in failed:
                        st.markdown(f"- {item['name']}: {item.get('fix') or item.get('detail')}")

    with tab_complete:
        st.caption("Track agency sign-off using docs/COMPLETENESS.md criteria.")
        if "completeness" not in st.session_state:
            st.session_state["completeness"] = {}
        items = agency.load_completeness_items()
        done = 0
        for i, row in enumerate(items[:24]):
            key = f"cmp_{i}"
            checked = st.checkbox(row["item"], key=key, value=st.session_state["completeness"].get(key, False))
            st.session_state["completeness"][key] = checked
            if checked:
                done += 1
            if row.get("verify"):
                st.caption(f"Verify: {row['verify']}")
        if items:
            pct = round(100.0 * done / len(items[:24]), 1)
            st.progress(done / len(items[:24]), text=f"Completeness: {pct}% ({done}/{min(24, len(items))})")

    with tab_health:
        health = agency.system_health()
        st.metric("System health", f"{health['score']:.0f}%")
        for check in health["checks"]:
            label = f"{'✅' if check['ok'] else '❌'} {check['name']}"
            detail = check.get("detail") or check.get("fix", "")
            st.markdown(f"{label} {detail}")

    with tab_logs:
        rows = agency.tail_ingest_log(40)
        if not rows:
            st.info("No ingestion events yet. Load a workflow to populate outputs/logs/ingest.jsonl.")
        else:
            st.dataframe(rows, use_container_width=True, hide_index=True)
