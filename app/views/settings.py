"""Settings, readiness, completeness, health, and cache management."""

from __future__ import annotations

import streamlit as st

from app.data_loader import cache_freshness_report
from app.services import agency
from app.ui.theme import render_readiness_bars, render_quality_badge
from app.utils.i18n import t
from socrata_toolkit.core.readiness import run_readiness_checks


def render_settings_page() -> None:
    st.subheader(f"⚙️ {t('settings_title')}")

    tab_ready, tab_complete, tab_health, tab_cache, tab_logs = st.tabs([
        f"🎯 {t('tab_readiness')}",
        f"✅ {t('tab_completeness')}",
        f"🩺 {t('tab_health')}",
        "💾 Cache",
        f"📋 {t('tab_logs')}",
    ])

    # ------------------------------------------------------------------
    with tab_ready:
        report = run_readiness_checks()
        overall = report.get("overall_score", 0)
        badge_html = render_quality_badge(overall)
        st.markdown(
            f"Overall readiness: {badge_html}",
            unsafe_allow_html=True,
        )
        render_readiness_bars(report.get("axis_scores", {}))
        if note := report.get("note"):
            st.caption(note)

        with st.expander("❌ Failed checks", expanded=overall < 80):
            failed_count = 0
            for axis, items in report.get("axes", {}).items():
                failed = [i for i in items if not i.get("ok")]
                if failed:
                    st.markdown(f"**{axis.replace('_', ' ').title()}**")
                    for item in failed:
                        fix = item.get("fix") or item.get("detail") or ""
                        st.markdown(f"- ❌ **{item['name']}**: {fix}")
                        failed_count += 1
            if failed_count == 0:
                st.success("✅ All readiness checks pass!")

        with st.expander("✅ Passing checks"):
            for axis, items in report.get("axes", {}).items():
                passed = [i for i in items if i.get("ok")]
                for item in passed:
                    st.markdown(f"- ✅ **{item['name']}**")

    # ------------------------------------------------------------------
    with tab_complete:
        st.caption("Track agency sign-off criteria from `docs/COMPLETENESS.md`.")
        if "completeness" not in st.session_state:
            st.session_state["completeness"] = {}

        items = agency.load_completeness_items()
        if not items:
            st.warning("No completeness items found. Check `docs/COMPLETENESS.md`.")
        else:
            done = 0
            total = min(24, len(items))
            for i, row in enumerate(items[:total]):
                key = f"cmp_{i}"
                checked = st.checkbox(
                    row["item"],
                    key=key,
                    value=st.session_state["completeness"].get(key, False),
                )
                st.session_state["completeness"][key] = checked
                if checked:
                    done += 1
                if row.get("verify"):
                    st.caption(f"Verify: `{row['verify']}`")

            pct = round(100.0 * done / total, 1)
            color = "normal" if pct >= 80 else ("inverse" if pct < 40 else "off")
            st.progress(done / total, text=f"Completeness: {pct}% ({done}/{total})")
            st.metric("Sign-off progress", f"{pct}%", delta=f"{done}/{total} items")

            if st.button("Reset checklist"):
                st.session_state["completeness"] = {}
                st.rerun()

    # ------------------------------------------------------------------
    with tab_health:
        health = agency.system_health()
        score = health["score"]

        c1, c2 = st.columns([1, 2])
        c1.metric("System health", f"{score:.0f}%")
        c2.caption(f"Checked at: {health.get('checked_at', 'unknown')}")

        ok_items = [c for c in health["checks"] if c["ok"]]
        fail_items = [c for c in health["checks"] if not c["ok"]]

        if fail_items:
            st.error(f"⚠️ {len(fail_items)} check(s) need attention:")
            for check in fail_items:
                detail = check.get("detail") or check.get("fix", "")
                st.markdown(f"- ❌ **{check['name']}**: {detail}")

        if ok_items:
            with st.expander(f"✅ {len(ok_items)} passing checks"):
                for check in ok_items:
                    detail = check.get("detail", "")
                    st.markdown(f"- ✅ **{check['name']}**{': ' + detail if detail else ''}")

        if st.button("🔄 Re-run health check"):
            st.cache_data.clear()
            st.rerun()

    # ------------------------------------------------------------------
    with tab_cache:
        st.caption("Parquet cache status for Socrata datasets.")
        df = cache_freshness_report()
        if df.empty:
            st.info("No parquet caches exist yet. Load a workflow to create them.")
        else:
            fresh_count = int(df["fresh"].sum())
            stale_count = len(df) - fresh_count
            c1, c2, c3 = st.columns(3)
            c1.metric("Cached datasets", len(df))
            c2.metric("Fresh (< 24h)", fresh_count)
            c3.metric("Stale (> 24h)", stale_count, delta_color="inverse")
            st.dataframe(df, use_container_width=True, hide_index=True)

        if st.button("🗑️ Clear all parquet caches", type="secondary"):
            from pathlib import Path
            cache_dir = Path(__file__).resolve().parents[2] / "data" / "local_db" / "socrata_cache"
            cleared = 0
            if cache_dir.exists():
                for f in cache_dir.glob("*.parquet"):
                    f.unlink()
                    cleared += 1
            st.success(f"Cleared {cleared} cache file(s).")
            st.rerun()

    # ------------------------------------------------------------------
    with tab_logs:
        rows = agency.tail_ingest_log(50)
        if not rows:
            st.info(
                "No ingestion events yet. Load a workflow to populate "
                "`outputs/logs/ingest.jsonl`."
            )
        else:
            import pandas as pd

            log_df = pd.DataFrame(rows)
            c1, c2 = st.columns([3, 1])
            c1.caption(f"Showing last {len(rows)} events from ingest log.")
            filter_event = c2.selectbox(
                "Filter event type",
                ["all"] + sorted(log_df.get("event", pd.Series()).unique().tolist() if "event" in log_df.columns else []),
            )
            if filter_event != "all" and "event" in log_df.columns:
                log_df = log_df[log_df["event"] == filter_event]

            st.dataframe(log_df, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇ Export log (CSV)",
                log_df.to_csv(index=False).encode("utf-8"),
                "ingest_log.csv",
                mime="text/csv",
            )
