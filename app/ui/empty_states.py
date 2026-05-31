"""Empty states and guided tour for non-technical users."""

from __future__ import annotations

import os
from collections.abc import Callable

import streamlit as st

from app.utils.i18n import t


def render_empty_state(*, on_load_demo: Callable[[], None] | None = None) -> None:
    st.info(f"**{t('empty_title')}** — {t('empty_body')}")
    col1, col2 = st.columns(2)
    with col1:
        if st.button(t("load_sample"), type="primary", key="empty_load_demo"):
            os.environ["MISSION_DEMO"] = "1"
            if on_load_demo:
                on_load_demo()
            st.session_state["workflow_data_loaded"] = True
            st.rerun()
        st.caption(t("upload_prompt"))
    with col2:
        uploaded = st.file_uploader(t("upload_csv"), type=["csv"], key="empty_csv_upload")
        if uploaded is not None:
            import pandas as pd

            df = pd.read_csv(uploaded)
            st.session_state["uploaded_csv"] = df
            st.session_state["workflow_data_loaded"] = True
            st.success(f"Loaded {len(df):,} rows from {uploaded.name}")
    st.markdown("---")
    st.markdown(t("new_here"))


def render_guided_tour() -> None:
    with st.expander(t("tour_title"), expanded=not st.session_state.get("tour_seen")):
        st.markdown(t("tour_step1"))
        st.markdown(t("tour_step2"))
        st.markdown(t("tour_step3"))
        st.markdown(t("tour_step4"))
        if st.button("Got it / Entendido", key="tour_done"):
            st.session_state["tour_seen"] = True
            st.rerun()


def frames_are_empty(frames: dict) -> bool:
    if not frames:
        return True
    for df in frames.values():
        if getattr(df, "empty", True) is False and "_error" not in getattr(df, "columns", []):
            return False
    return True
