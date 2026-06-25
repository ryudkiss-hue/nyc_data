"""Home / onboarding — enhanced dashboard view."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import streamlit as st

from app.data_loader import DATASET_REGISTRY, demo_mode_enabled, token_status
from app.services import agency
from app.ui.empty_states import render_empty_state, render_guided_tour
from app.utils.i18n import t

# ---------------------------------------------------------------------------
# Live Metric helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def _fetch_live_metric_data() -> dict:
    """Fetch raw Metric counts from the Socrata cache/manifest.

    Uses only already-cached parquet data to avoid blocking the page load.
    Falls back to zeros if data is not available (no live Socrata call needed
    here — the workflow loaders handle that separately).
    """
    import json
    from pathlib import Path

    result: dict = {
        "pending_inspections": None,
        "active_conflicts": None,
        "sla_health_pct": None,
        "cache_age_hours": None,
    }

    # Attempt to read from parquet cache (no network call)
    cache_dir = Path(__file__).resolve().parents[2] / "data" / "local_db" / "socrata_cache"
    manifest_path = Path(__file__).resolve().parents[2] / "data" / "cache" / "manifest.json"

    # Cache age from manifest
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            # Use the most recently fetched dataset as a proxy for overall cache age
            fetch_times = [
                entry.get("fetched_at")
                for entry in manifest.values()
                if isinstance(entry, dict) and entry.get("fetched_at")
            ]
            if fetch_times:
                most_recent = max(fetch_times)
                fetched_dt = datetime.fromisoformat(most_recent.replace("Z", "+00:00"))
                age_sec = (datetime.now(timezone.utc) - fetched_dt).total_seconds()
                result["cache_age_hours"] = round(age_sec / 3600, 1)
        except (ValueError, KeyError, OSError):
            pass

    # Attempt to read inspection parquet for pending/SLA counts
    inspection_parquet = cache_dir / "inspection.parquet"
    if inspection_parquet.exists():
        try:
            import pandas as pd

            df = pd.read_parquet(inspection_parquet)
            if not df.empty:
                # Pending = rows where status is not closed/resolved
                status_col = next(
                    (c for c in df.columns if c.lower() in ("status", "inspection_status", "case_status")),
                    None,
                )
                if status_col:
                    closed_terms = {"closed", "resolved", "completed", "done"}
                    pending_mask = ~df[status_col].astype(str).str.lower().isin(closed_terms)
                    result["pending_inspections"] = int(pending_mask.sum())

                    # SLA health: closed within grace period (proxy: closed in < 30 days)
                    date_col = next(
                        (c for c in df.columns if "date" in c.lower() or "created" in c.lower()),
                        None,
                    )
                    closed_df = df[~pending_mask].copy()
                    if date_col and len(closed_df) > 0:
                        try:
                            closed_df["_date"] = pd.to_datetime(
                                closed_df[date_col], errors="coerce", utc=True
                            )
                            now_utc = pd.Timestamp.now(tz="UTC")
                            within_sla = (
                                (now_utc - closed_df["_date"]).dt.total_seconds() / 86400
                            ) <= 30
                            sla_pct = within_sla.mean() * 100 if len(closed_df) > 0 else None
                            result["sla_health_pct"] = round(sla_pct, 1) if sla_pct is not None else None
                        except (TypeError, AttributeError):
                            pass
                else:
                    result["pending_inspections"] = len(df)
        except (OSError, ValueError, ImportError):
            pass

    # Active conflicts from permits/work-orders parquet
    for conflict_key in ("street_permits", "work_orders", "permits"):
        conflict_parquet = cache_dir / f"{conflict_key}.parquet"
        if conflict_parquet.exists():
            try:
                import pandas as pd

                df = pd.read_parquet(conflict_parquet)
                if not df.empty:
                    status_col = next(
                        (c for c in df.columns if c.lower() in ("status", "permit_status", "order_status")),
                        None,
                    )
                    if status_col:
                        active_terms = {"active", "open", "in progress", "issued", "approved"}
                        active_mask = df[status_col].astype(str).str.lower().isin(active_terms)
                        result["active_conflicts"] = int(active_mask.sum())
                    else:
                        result["active_conflicts"] = len(df)
                    break
            except (OSError, ValueError, ImportError):
                pass

    return result

def _make_live_metrics_fragment():
    """Build and return the live-Metric render function.

    Wraps with ``@st.fragment(run_every=300)`` when available (Streamlit ≥ 1.33),
    otherwise returns a plain callable.
    """

    def _render_live_metrics_inner() -> None:
        st.markdown("#### 🔴 Live Metrics")
        st.caption("Auto-refreshes every 5 minutes from local cache")

        with st.status("Loading Metric data…", expanded=False) as status_box:
            metric_data = _fetch_live_metric_data()
            status_box.update(label="Metric data loaded", state="complete", expanded=False)

        k1, k2, k3, k4 = st.columns(4)

        pending = metric_data.get("pending_inspections")
        k1.metric(
            "Pending Inspections",
            f"{pending:,}" if pending is not None else "—",
            help="Open inspections where status != Closed/Resolved (from local cache)",
        )

        conflicts = metric_data.get("active_conflicts")
        k2.metric(
            "Active Conflicts",
            f"{conflicts:,}" if conflicts is not None else "—",
            help="Active/open work orders or permits that may overlap (from local cache)",
        )

        sla = metric_data.get("sla_health_pct")
        k3.metric(
            "SLA Health %",
            f"{sla:.1f}%" if sla is not None else "—",
            delta="On track" if sla is not None and sla >= 80 else None,
            delta_color="normal" if sla is not None and sla >= 80 else "off",
            help="% of closed inspections resolved within 30-day SLA proxy (from local cache)",
        )

        cache_age = metric_data.get("cache_age_hours")
        if cache_age is None:
            age_label = "No cache"
        elif cache_age < 1:
            age_label = "< 1h ago"
        else:
            age_label = f"{cache_age:.1f}h ago"
        k4.metric(
            "Cache Age",
            age_label,
            help="Hours since last Socrata fetch (from cache manifest)",
        )

        if all(v is None for v in metric_data.values()):
            st.caption(
                "ℹ️ No cached data found. Run a workflow to populate Metrics."
            )

    if hasattr(st, "fragment"):
        return st.fragment(run_every=300)(_render_live_metrics_inner)
    return _render_live_metrics_inner

# Build the fragment once at module import so we reuse the decorated version.
render_live_metrics = _make_live_metrics_fragment()

# ---------------------------------------------------------------------------
# Home page
# ---------------------------------------------------------------------------

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

    # ---- Live Metric tiles (fragment rerender every 5 min) ----
    render_live_metrics()

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
            if st.button("Open QA/QC", use_container_width=True):
                st.session_state["_quick_nav"] = "qa"
    with qa2:
        with st.container(border=True):
            st.markdown("**🗺️ Spatial Conflicts**")
            st.caption("Detect construction schedule intersections")
            if st.button("Open Spatial", use_container_width=True):
                st.session_state["_quick_nav"] = "spatial"
    with qa3:
        with st.container(border=True):
            st.markdown("**🩺 Data Quality**")
            st.caption("Column profiling and quality scores")
            if st.button("Open Quality", use_container_width=True):
                st.session_state["_quick_nav"] = "quality"
    with qa4:
        with st.container(border=True):
            st.markdown("**📥 Ingest Matrix**")
            st.caption("All datasets with row counts and status")
            if st.button("Open Ingest", use_container_width=True):
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
        st.dataframe(log_df, use_container_width=True, hide_index=True)
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
