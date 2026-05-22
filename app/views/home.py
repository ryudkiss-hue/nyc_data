"""Home / onboarding."""

from __future__ import annotations

import os

import streamlit as st

from app.data_loader import demo_mode_enabled, token_status
from app.services import agency
from app.ui.empty_states import render_empty_state, render_guided_tour
from app.utils.i18n import t


def render_home_page() -> None:
    st.subheader(t("welcome"))
    st.caption(t("welcome_sub"))

    render_guided_tour()

    token = token_status()
    if not st.session_state.get("onboarding_done"):
        with st.container(border=True):
            st.markdown(f"**{t('onboarding_title')}**")
            for i, step in enumerate(agency.onboarding_steps(), start=1):
                st.markdown(f"{i}. {step}")
            if st.button(t("onboarding_done")):
                st.session_state["onboarding_done"] = True
                st.rerun()
    else:
        st.success(t("onboarding_complete_msg"))

    if not st.session_state.get("workflow_data_loaded") and not token["configured"] and not token.get("key_pair"):
        render_empty_state(on_load_demo=lambda: os.environ.setdefault("MISSION_DEMO", "1"))

    c1, c2, c3 = st.columns(3)
    c1.metric(t("metric_datasets"), token["datasets"])
    auth_label = t("auth_configured") if token["configured"] or token.get("key_pair") else t("auth_demo")
    c2.metric(t("metric_auth"), auth_label)
    latest = agency.latest_pack_dir()
    c3.metric(t("metric_pack"), latest.name if latest else "—")

    if demo_mode_enabled():
        st.info("Demo mode / Modo demo — add `SOCRATA_APP_TOKEN` to `.env` for production.")

    st.markdown("**Docs** — `docs/AGENCY_RUNBOOK.md` · `docs/SIMPLE_START.md` · `socrata readiness` · `socrata doctor`")
