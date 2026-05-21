"""Home / onboarding."""

from __future__ import annotations

import streamlit as st

from app.data_loader import demo_mode_enabled, token_status
from app.services import agency


def render_home_page() -> None:
    st.subheader("Welcome")
    token = token_status()
    if not st.session_state.get("onboarding_done"):
        with st.container(border=True):
            st.markdown("**First-time setup**")
            for i, step in enumerate(agency.onboarding_steps(), start=1):
                st.markdown(f"{i}. {step}")
            if st.button("Mark onboarding complete"):
                st.session_state["onboarding_done"] = True
                st.rerun()
    else:
        st.success("Onboarding complete. Use the sidebar to open analyst workflows.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Socrata datasets", token["datasets"])
    c2.metric("Auth", "Configured" if token["configured"] or token.get("key_pair") else "Demo / public")
    latest = agency.latest_pack_dir()
    c3.metric("Latest pack", latest.name if latest else "—")

    if demo_mode_enabled():
        st.info("Running in **demo mode**. Add `SOCRATA_APP_TOKEN` to `.env` for production data.")

    st.markdown("**Quick links**")
    st.markdown(
        "- [Agency runbook](docs/AGENCY_RUNBOOK.md) · "
        "- [Simple start](docs/SIMPLE_START.md) · "
        "- `socrata readiness` · "
        "- `socrata doctor`"
    )
