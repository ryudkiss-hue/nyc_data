"""Publish & analyst pack operations."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.services import agency


def render_publish_page() -> None:
    st.subheader("Publish & Analyst Pack")
    st.caption("Run the weekly pack, then publish to share paths, email, or BI (dry-run first).")

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
        offline = st.checkbox("Offline pack run", value=False)
        if st.button("Run Analyst Pack", type="primary", key="run_pack"):
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
        dry_run = st.checkbox("Dry run (recommended)", value=True)
        if st.button("Publish pack", key="publish_pack") and pack_dir:
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
