"""Home / onboarding — enhanced dashboard view."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import streamlit as st

from app.data_loader import DATASET_REGISTRY, demo_mode_enabled, token_status
from app.services import agency
from app.ui.empty_states import render_empty_state, render_guided_tour
from app.utils.i18n import t


def _format_age(path_mtime: float) -> str:
    """Human-readable age from a file mtime."""
    age_sec = datetime.now(timezone.utc).timestamp() - path_mtime
    if age_sec < 3600:
        return f"{int(age_sec / 60)}m ago"
    if age_sec < 86400:
        return f"{int(age_sec / 3600)}h ago"
    return f"{int(age_sec / 86400)}d ago"


def render_home_page() -> None:
    st.subheader(t("welcome"))
    st.caption(t("welcome_sub"))

    render_guided_tour()
    token = token_status()

    # ---- Status overview ----
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Registered datasets",
        token["datasets"],
        help="Total datasets in config/datasets.yaml",
    )
    auth_label = (
        "🔐 Configured"
        if (token["configured"] or token.get("key_pair"))
        else "🟡 Public / Demo"
    )
    c2.metric("API auth status", auth_label)
    latest_pack = agency.latest_pack_dir()
    pack_label = latest_pack.name if latest_pack else "—"
    pack_age = (
        _format_age(latest_pack.stat().st_mtime)
        if latest_pack and latest_pack.exists()
        else ""
    )
    c3.metric("Latest analyst pack", pack_label, delta=pack_age or None)

    health = agency.system_health()
    c4.metric(
        "System health",
        f"{health['score']:.0f}%",
        delta="All checks pass" if health["score"] >= 85 else "See Settings → Health",
        delta_color="normal" if health["score"] >= 85 else "inverse",
    )

    st.divider()

    # ---- Onboarding ----
    if not st.session_state.get("onboarding_done"):
        with st.container(border=True):
            st.markdown(f"#### 🚀 {t('onboarding_title')}")
            steps = agency.onboarding_steps()
            for i, step in enumerate(steps, start=1):
                icon = "✅" if i <= 2 else "⬜"
                st.markdown(f"{icon} **Step {i}:** {step}")
            if st.button(t("onboarding_done"), type="primary"):
                st.session_state["onboarding_done"] = True
                st.rerun()
    else:
        st.success(f"✅ {t('onboarding_complete_msg')} — Ready for analyst workflows.")

    # ---- Quick actions ----
    st.markdown("#### Quick Actions")
    qa1, qa2, qa3, qa4 = st.columns(4)
    with qa1:
        with st.container(border=True):
            st.markdown("**🔍 QA/QC Ledger**")
            st.caption("Cross-check lot ownership against MapPLUTO")
            if st.button("Open QA/QC", width="stretch"):
                st.session_state["_quick_nav"] = "qa"
    with qa2:
        with st.container(border=True):
            st.markdown("**🗺️ Spatial Conflicts**")
            st.caption("Detect construction schedule intersections")
            if st.button("Open Spatial", width="stretch"):
                st.session_state["_quick_nav"] = "spatial"
    with qa3:
        with st.container(border=True):
            st.markdown("**🩺 Data Quality**")
            st.caption("Column profiling and quality scores")
            if st.button("Open Quality", width="stretch"):
                st.session_state["_quick_nav"] = "quality"
    with qa4:
        with st.container(border=True):
            st.markdown("**📥 Ingest Matrix**")
            st.caption("All datasets with row counts and status")
            if st.button("Open Ingest", width="stretch"):
                st.session_state["_quick_nav"] = "ingest"

    # ---- Dataset registry summary ----
    st.divider()
    st.markdown("#### Registered Datasets by Group")
    groups: dict[str, list[str]] = {}
    for key, meta in DATASET_REGISTRY.items():
        g = meta.get("group", "other")
        groups.setdefault(g, []).append(f"`{key}` — {meta.get('label', key)}")

    gcols = st.columns(min(len(groups), 4))
    for idx, (grp, items) in enumerate(groups.items()):
        with gcols[idx % len(gcols)]:
            with st.container(border=True):
                st.markdown(f"**{grp.replace('_', ' ').title()}** ({len(items)})")
                for item in items:
                    st.markdown(f"• {item}")

    # ---- Demo mode notice ----
    if not st.session_state.get("workflow_data_loaded") and not token["configured"] and not token.get("key_pair"):
        st.divider()
        render_empty_state(on_load_demo=lambda: os.environ.setdefault("MISSION_DEMO", "1"))

    if demo_mode_enabled():
        st.info(
            "ℹ️ **Demo mode active** — set `SOCRATA_APP_TOKEN` in `.env` for live Socrata data.\n\n"
            "Demo data is synthetic and suitable for testing workflows only."
        )

    # ---- Recent ingestion log ----
    st.divider()
    st.markdown("#### Recent Ingestion Activity")
    rows = agency.tail_ingest_log(10)
    if rows:
        import pandas as pd

        log_df = pd.DataFrame(rows)
        st.dataframe(log_df, width="stretch", hide_index=True)
    else:
        st.caption("No ingestion events yet. Load a workflow to see activity here.")

    st.divider()
    st.markdown(
        "📖 **Documentation** · "
        "`docs/AGENCY_RUNBOOK.md` · "
        "`docs/SIMPLE_START.md` · "
        "`socrata readiness` · "
        "`socrata doctor`"
    )
