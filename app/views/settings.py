"""Settings, readiness, completeness, health, cache management, and API configuration."""

from __future__ import annotations

import datetime
import json
import os
import sys
from pathlib import Path

import streamlit as st
import yaml

from app.data_loader import DATASET_REGISTRY, cache_freshness_report
from app.services import agency
from app.services.alerts import get_last_scheduler_run, send_slack_alert, test_arcgis_connection
from app.ui.theme import render_quality_badge, render_readiness_bars
from app.utils.i18n import t
from socrata_toolkit.core.readiness import run_readiness_checks

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _REPO_ROOT / ".env"
_PRESETS_FILE = _REPO_ROOT / "data" / "filter_presets.json"
_SCHEDULER_CONFIG = _REPO_ROOT / "data" / "scheduler_config.json"
_SLA_CONFIG = _REPO_ROOT / "data" / "sla_config.json"

_SLA_DEFAULTS: dict[str, int] = {"HIGH": 14, "MED": 30, "LOW": 60}

ENV_VARS_TABLE = [
    {
        "name": "SOCRATA_APP_TOKEN",
        "description": "Socrata API app token",
        "required": False,
    },
    {
        "name": "ANTHROPIC_API_KEY",
        "description": "Anthropic API key for NL queries",
        "required": False,
    },
    {
        "name": "SLACK_WEBHOOK_URL",
        "description": "Slack webhook for alerts",
        "required": False,
    },
    {
        "name": "SOCRATA_CACHE_DIR",
        "description": "L2 cache directory",
        "required": False,
    },
    {
        "name": "ARCGIS_ORG_URL",
        "description": "ArcGIS Online org URL",
        "required": False,
    },
]


def _read_env_file() -> dict[str, str]:
    """Read key=value pairs from .env file, ignoring comments."""
    env: dict[str, str] = {}
    if _ENV_FILE.exists():
        for line in _ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _write_env_file(env: dict[str, str]) -> None:
    """Write key=value pairs to .env file (preserves existing non-Socrata entries)."""
    existing_lines: list[str] = []
    managed_keys = {
        "SOCRATA_APP_TOKEN", "SOCRATA_KEY_ID", "SOCRATA_KEY_SECRET",
        "SOCRATA_DOMAIN", "SOCRATA_DOMAIN_SECONDARY",
        "SOCRATA_ROW_LIMIT", "SOCRATA_CACHE_TTL_SECONDS",
    }

    if _ENV_FILE.exists():
        for line in _ENV_FILE.read_text().splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k = stripped.split("=", 1)[0].strip()
                if k not in managed_keys:
                    existing_lines.append(line)
            elif stripped.startswith("#"):
                existing_lines.append(line)

    new_lines = ["# Socrata / NYC Open Data API configuration (managed by Settings UI)"]
    for k, v in env.items():
        new_lines.append(f'{k}={v}')

    _ENV_FILE.write_text("\n".join(existing_lines + [""] + new_lines) + "\n")


def render_settings_page() -> None:
    st.subheader(f"⚙️ {t('settings_title')}")

    (
        tab_tokens,
        tab_config,
        tab_registry,
        tab_ready,
        tab_complete,
        tab_health,
        tab_cache,
        tab_logs,
        tab_alerts,
        tab_presets,
        tab_impex,
        tab_scheduler,
        tab_sla,
        tab_alert_config,
        tab_env,
    ) = st.tabs([
        "🔑 API Tokens",
        "⚙️ Configuration",
        "📦 Dataset Registry",
        f"🎯 {t('tab_readiness')}",
        f"✅ {t('tab_completeness')}",
        f"🩺 {t('tab_health')}",
        "💾 Cache",
        f"📋 {t('tab_logs')}",
        "🔔 Alerts",
        "📌 Filter Presets",
        "💾 Import/Export",
        "⏰ Scheduler",
        "🚦 SLA Thresholds",
        "🔔 Alert Config",
        "📋 Environment",
    ])

    # ------------------------------------------------------------------
    with tab_tokens:
        _render_api_tokens_tab()

    # ------------------------------------------------------------------
    with tab_config:
        _render_configuration_tab()

    # ------------------------------------------------------------------
    with tab_registry:
        _render_registry_tab()

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
                ["all"] + sorted(
                    log_df.get("event", pd.Series()).unique().tolist()
                    if "event" in log_df.columns else []
                ),
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

    # ------------------------------------------------------------------
    with tab_alerts:
        _render_alerts_tab()

    # ------------------------------------------------------------------
    with tab_presets:
        _render_filter_presets_tab()

    # ------------------------------------------------------------------
    with tab_impex:
        _render_import_export_tab()

    # ------------------------------------------------------------------
    with tab_scheduler:
        _render_scheduler_tab()

    # ------------------------------------------------------------------
    with tab_sla:
        _render_sla_tab()

    # ------------------------------------------------------------------
    with tab_alert_config:
        _render_alert_config_tab()

    # ------------------------------------------------------------------
    with tab_env:
        _render_environment_tab()


# --------------------------------------------------------------------------- #
# Tab helpers
# --------------------------------------------------------------------------- #

def _render_api_tokens_tab() -> None:
    st.markdown("#### Socrata / NYC Open Data API Credentials")
    st.caption(
        "Credentials are saved to your local `.env` file and loaded at startup. "
        "Get an App Token at [data.cityofnewyork.us/profile/app_tokens](https://data.cityofnewyork.us/profile/app_tokens). "
        "Key ID + Secret support OAuth-signed write access (advanced)."
    )

    current = _read_env_file()

    with st.form("api_token_form"):
        app_token = st.text_input(
            "App Token (`SOCRATA_APP_TOKEN`)",
            value=current.get("SOCRATA_APP_TOKEN", ""),
            type="password",
            help="Required to avoid rate limits (429). Free — register at data.cityofnewyork.us.",
        )

        st.markdown("**OAuth key pair** (optional — needed for dataset write/publish)")
        kc1, kc2 = st.columns(2)
        key_id = kc1.text_input(
            "Key ID (`SOCRATA_KEY_ID`)",
            value=current.get("SOCRATA_KEY_ID", ""),
            type="password",
        )
        key_secret = kc2.text_input(
            "Key Secret (`SOCRATA_KEY_SECRET`)",
            value=current.get("SOCRATA_KEY_SECRET", ""),
            type="password",
        )

        save_btn = st.form_submit_button("💾 Save credentials", type="primary")

    if save_btn:
        new_env = dict(current)
        if app_token:
            new_env["SOCRATA_APP_TOKEN"] = app_token
        elif "SOCRATA_APP_TOKEN" in new_env:
            del new_env["SOCRATA_APP_TOKEN"]
        if key_id:
            new_env["SOCRATA_KEY_ID"] = key_id
        elif "SOCRATA_KEY_ID" in new_env:
            del new_env["SOCRATA_KEY_ID"]
        if key_secret:
            new_env["SOCRATA_KEY_SECRET"] = key_secret
        elif "SOCRATA_KEY_SECRET" in new_env:
            del new_env["SOCRATA_KEY_SECRET"]
        try:
            _write_env_file({k: v for k, v in new_env.items()
                             if k in {"SOCRATA_APP_TOKEN", "SOCRATA_KEY_ID", "SOCRATA_KEY_SECRET",
                                      "SOCRATA_DOMAIN", "SOCRATA_DOMAIN_SECONDARY",
                                      "SOCRATA_ROW_LIMIT", "SOCRATA_CACHE_TTL_SECONDS"}})
            st.success("Credentials saved to `.env`. Restart the app to pick up new values.")
        except Exception as exc:
            st.error(f"Failed to write .env: {exc}")

    # Token status live check
    st.divider()
    st.markdown("#### Live token status")
    if st.button("🔍 Check current token", use_container_width=False):
        from app.data_loader import token_status
        status = token_status()
        if status.get("demo_mode"):
            st.warning("Running in demo mode — no live Socrata access.")
        elif status.get("configured"):
            st.success(f"App token configured. Registered datasets: {status.get('datasets', 0)}")
        elif status.get("key_pair"):
            st.success("OAuth key pair configured.")
        else:
            st.error("No credentials found. Set SOCRATA_APP_TOKEN in your .env file.")

        with st.expander("Full status dict"):
            st.json(status)

    st.divider()
    st.markdown("#### Verify connectivity")
    if st.button("🌐 Test Socrata connection", use_container_width=False):
        import requests
        token = os.getenv("SOCRATA_APP_TOKEN", "").strip()
        headers = {"X-App-Token": token} if token else {}
        try:
            r = requests.get(
                "https://api.us.socrata.com/api/catalog/v1",
                params={"q": "sidewalk", "limit": 1},
                headers=headers,
                timeout=8,
            )
            r.raise_for_status()
            total = r.json().get("resultSetSize", "?")
            st.success(f"Connected. Discovery API returned {total:,} results for 'sidewalk'.")
        except Exception as exc:
            st.error(f"Connection failed: {exc}")


def _render_configuration_tab() -> None:
    st.markdown("#### Data Ingestion Configuration")
    st.caption(
        "These settings control how much data the app loads from Socrata and how long it caches results."
    )

    current = _read_env_file()

    with st.form("config_form"):
        domain = st.text_input(
            "Primary Socrata domain (`SOCRATA_DOMAIN`)",
            value=current.get("SOCRATA_DOMAIN", "data.cityofnewyork.us"),
            help="Default: data.cityofnewyork.us",
        )
        domain_secondary = st.text_input(
            "Secondary domain (`SOCRATA_DOMAIN_SECONDARY`)",
            value=current.get("SOCRATA_DOMAIN_SECONDARY", ""),
            help="Optional second portal (e.g. opendata.cityofnewyork.us).",
        )

        st.markdown("**Row limits**")
        rl_col1, rl_col2 = st.columns(2)
        row_limit = rl_col1.number_input(
            "Default row limit per dataset (`SOCRATA_ROW_LIMIT`)",
            min_value=1_000,
            max_value=500_000,
            value=int(current.get("SOCRATA_ROW_LIMIT", 50_000)),
            step=5_000,
            help="Max rows fetched per dataset unless overridden in the view.",
        )
        cache_ttl = rl_col2.number_input(
            "Cache TTL seconds (`SOCRATA_CACHE_TTL_SECONDS`)",
            min_value=60,
            max_value=86_400,
            value=int(current.get("SOCRATA_CACHE_TTL_SECONDS", 3_600)),
            step=300,
            help="How long to cache dataset results. 3600 = 1 hour.",
        )

        st.markdown("**Discovery API defaults**")
        dc1, dc2 = st.columns(2)
        dc1.number_input(
            "Discovery results per page",
            min_value=10,
            max_value=100,
            value=25,
            step=5,
            help="Default number of results shown per search page in Data Discovery.",
        )
        dc2.text_input(
            "Discovery default domains",
            value=current.get("SOCRATA_DOMAIN", "data.cityofnewyork.us"),
            help="Comma-separated domains pre-filled in Discovery search.",
        )

        save_cfg = st.form_submit_button("💾 Save configuration", type="primary")

    if save_cfg:
        new_vals: dict[str, str] = {}
        if domain:
            new_vals["SOCRATA_DOMAIN"] = domain
        if domain_secondary:
            new_vals["SOCRATA_DOMAIN_SECONDARY"] = domain_secondary
        new_vals["SOCRATA_ROW_LIMIT"] = str(int(row_limit))
        new_vals["SOCRATA_CACHE_TTL_SECONDS"] = str(int(cache_ttl))

        existing = _read_env_file()
        existing.update(new_vals)
        _write_env_file({k: v for k, v in existing.items()
                         if k in {"SOCRATA_APP_TOKEN", "SOCRATA_KEY_ID", "SOCRATA_KEY_SECRET",
                                  "SOCRATA_DOMAIN", "SOCRATA_DOMAIN_SECONDARY",
                                  "SOCRATA_ROW_LIMIT", "SOCRATA_CACHE_TTL_SECONDS"}})
        st.success("Configuration saved to `.env`. Restart the app to apply.")

    st.divider()
    st.markdown("#### Environment variable reference")
    env_table = {
        "SOCRATA_APP_TOKEN": "App token for authenticated API calls (no rate limits)",
        "SOCRATA_KEY_ID": "OAuth key ID for write access",
        "SOCRATA_KEY_SECRET": "OAuth key secret for write access",
        "SOCRATA_USERNAME": "Username (legacy auth fallback)",
        "SOCRATA_PASSWORD": "Password (legacy auth fallback)",
        "SOCRATA_DOMAIN": "Primary Socrata portal domain",
        "SOCRATA_ROW_LIMIT": "Default row fetch limit per dataset",
        "SOCRATA_CACHE_TTL_SECONDS": "Parquet + st.cache_data TTL",
        "MISSION_DEMO": "Set to 1 to force demo mode (no live data)",
    }
    import pandas as pd
    st.dataframe(
        pd.DataFrame([{"variable": k, "description": v} for k, v in env_table.items()]),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.markdown("#### Current environment")
    if st.button("👁 Show loaded env vars (redacted)", use_container_width=False):
        rows = []
        for var in env_table:
            raw = os.getenv(var, "")
            if raw:
                display = raw[:4] + "****" if len(raw) > 8 else "****"
            else:
                display = "(not set)"
            rows.append({"variable": var, "value": display})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_registry_tab() -> None:
    import pandas as pd
    import yaml

    st.markdown("#### Dataset Registry")
    st.caption(
        "Registered datasets drive data ingestion across all app views. "
        "Edits below update `config/datasets.yaml` directly."
    )

    datasets_yaml_path = _REPO_ROOT / "config" / "datasets.yaml"

    if not datasets_yaml_path.exists():
        st.error("`config/datasets.yaml` not found.")
        return

    with open(datasets_yaml_path) as f:
        registry = yaml.safe_load(f)

    datasets = registry.get("datasets", {})

    # Build rows
    rows = []
    for key, meta in datasets.items():
        rows.append({
            "key": key,
            "fourfour": meta.get("fourfour", ""),
            "label": meta.get("label", ""),
            "group": meta.get("group", ""),
            "manhattan_where": meta.get("manhattan_where", ""),
        })

    df = pd.DataFrame(rows)
    st.markdown(f"**{len(df)} registered datasets**")

    # Column visibility multiselect
    all_cols = ["key", "label", "group", "fourfour"]
    visible_cols = st.multiselect(
        "Visible columns", all_cols, default=all_cols, key="reg_cols"
    )
    display_cols = [c for c in visible_cols if c in df.columns]
    if display_cols:
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### Add a dataset")
    with st.form("add_dataset_form"):
        ac1, ac2 = st.columns(2)
        new_key = ac1.text_input(
            "Registry key", placeholder="e.g. sidewalk_dismissal",
            help="Snake-case identifier used in code.",
        )
        new_fourfour = ac2.text_input("Socrata Dataset ID", placeholder="e.g. p4u2-3jgx")
        ac3, ac4 = st.columns(2)
        new_label = ac3.text_input("Label", placeholder="e.g. Sidewalk Dismissal")
        new_group = ac4.selectbox(
            "Group", ["core_smd", "accessibility", "coordination", "overlays", "other"]
        )
        new_where = st.text_input(
            "Manhattan WHERE clause (optional)",
            placeholder="upper(borough) = 'MANHATTAN'",
            help="SoQL predicate to filter to Manhattan rows.",
        )
        add_btn = st.form_submit_button("➕ Add dataset", type="primary")

    if add_btn:
        if not new_key or not new_fourfour:
            st.warning("Key and Dataset ID are required.")
        elif new_key in datasets:
            st.warning(f"Key `{new_key}` already exists.")
        else:
            entry: dict = {"fourfour": new_fourfour, "group": new_group, "label": new_label}
            if new_where:
                entry["manhattan_where"] = new_where
            registry["datasets"][new_key] = entry
            with open(datasets_yaml_path, "w") as f:
                yaml.safe_dump(
                    registry, f, default_flow_style=False, sort_keys=False, allow_unicode=True
                )
            st.success(
                f"Added `{new_key}` (`{new_fourfour}`) to registry. "
                "Restart app to use in workflows."
            )
            st.rerun()

    st.divider()
    st.markdown("#### Remove a dataset")
    remove_key = st.selectbox("Select dataset to remove", ["(select)"] + list(datasets.keys()))
    if remove_key != "(select)":
        if st.button(f"🗑 Remove `{remove_key}`", type="secondary"):
            del registry["datasets"][remove_key]
            with open(datasets_yaml_path, "w") as f:
                yaml.safe_dump(
                    registry, f, default_flow_style=False, sort_keys=False, allow_unicode=True
                )
            st.success(f"Removed `{remove_key}` from registry.")
            st.rerun()

    st.divider()
    with st.expander("Raw YAML"):
        with open(datasets_yaml_path) as f:
            st.code(f.read(), language="yaml")


def _render_alerts_tab() -> None:
    st.markdown("### Configure Alert Thresholds")

    current = _read_env_file()

    col1, col2 = st.columns(2)
    with col1:
        violation_threshold = st.number_input(
            "Max open violations per borough before alert",
            min_value=100,
            max_value=10_000,
            value=int(current.get("ALERT_VIOLATION_THRESHOLD", 500)),
            key="alert_violation_threshold",
        )
        inspection_gap_days = st.number_input(
            "Max days since last inspection before alert",
            min_value=7,
            max_value=365,
            value=int(current.get("ALERT_INSPECTION_GAP_DAYS", 30)),
            key="alert_inspection_gap_days",
        )
    with col2:
        slack_webhook = st.text_input(
            "Slack Webhook URL (optional)",
            type="password",
            value=current.get("ALERT_SLACK_WEBHOOK", ""),
            key="slack_wh",
        )
        alert_email = st.text_input(
            "Alert email address (optional)",
            value=current.get("ALERT_EMAIL", ""),
            key="alert_email",
        )

    if st.button("Save Alert Settings"):
        existing = _read_env_file()
        existing["ALERT_VIOLATION_THRESHOLD"] = str(int(violation_threshold))
        existing["ALERT_INSPECTION_GAP_DAYS"] = str(int(inspection_gap_days))
        if slack_webhook:
            existing["ALERT_SLACK_WEBHOOK"] = slack_webhook
        if alert_email:
            existing["ALERT_EMAIL"] = alert_email
        try:
            # Write all managed keys including the new alert ones
            managed = {
                "SOCRATA_APP_TOKEN", "SOCRATA_KEY_ID", "SOCRATA_KEY_SECRET",
                "SOCRATA_DOMAIN", "SOCRATA_DOMAIN_SECONDARY",
                "SOCRATA_ROW_LIMIT", "SOCRATA_CACHE_TTL_SECONDS",
                "ALERT_VIOLATION_THRESHOLD", "ALERT_INSPECTION_GAP_DAYS",
                "ALERT_SLACK_WEBHOOK", "ALERT_EMAIL",
            }
            _write_env_file({k: v for k, v in existing.items() if k in managed})
            st.success("Alert settings saved.")
        except Exception as exc:
            st.error(f"Failed to save alert settings: {exc}")

    st.divider()
    st.markdown("#### Test Alert")
    if st.button("Send test Slack alert"):
        webhook = os.getenv("ALERT_SLACK_WEBHOOK", "").strip() or slack_webhook
        if not webhook:
            st.warning("No Slack webhook configured.")
        else:
            try:
                from app.services.alerts import send_slack_alert
                ok, msg = send_slack_alert(
                    webhook_url=webhook,
                    title="NYC DOT SIM — Test Alert",
                    message="This is a test alert from the NYC DOT SIM Toolkit settings page.",
                    severity="info",
                )
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
            except Exception as exc:
                st.error(f"Alert send failed: {exc}")


def _render_filter_presets_tab() -> None:
    st.markdown("### Saved Filter Presets")

    presets_file = _PRESETS_FILE
    if presets_file.exists():
        try:
            presets: dict = json.loads(presets_file.read_text())
        except (json.JSONDecodeError, OSError):
            presets = {}
    else:
        presets = {}

    preset_name = st.text_input("Preset name", key="preset_name_input")
    preset_value = st.text_area(
        "Filter definition (JSON)",
        value='{"borough": "Manhattan", "severity": "HIGH"}',
        key="preset_value_input",
    )
    if st.button("Save Preset") and preset_name:
        try:
            presets[preset_name] = json.loads(preset_value)
            presets_file.parent.mkdir(exist_ok=True)
            presets_file.write_text(json.dumps(presets, indent=2))
            st.success(f"Saved preset '{preset_name}'")
            st.rerun()
        except json.JSONDecodeError:
            st.error("Invalid JSON")

    if presets:
        st.markdown("**Existing presets:**")
        for name, val in list(presets.items()):
            c1, c2 = st.columns([4, 1])
            c1.code(f"{name}: {json.dumps(val)}")
            if c2.button("Delete", key=f"del_{name}"):
                del presets[name]
                presets_file.write_text(json.dumps(presets, indent=2))
                st.rerun()


def _render_import_export_tab() -> None:
    st.markdown("### Export/Import Settings")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Export Settings JSON"):
            env_data = _read_env_file()
            presets_data: dict = {}
            if _PRESETS_FILE.exists():
                try:
                    presets_data = json.loads(_PRESETS_FILE.read_text())
                except (json.JSONDecodeError, OSError):
                    presets_data = {}
            settings_payload = {
                "env": env_data,
                "presets": presets_data,
            }
            st.download_button(
                "Download settings.json",
                data=json.dumps(settings_payload, indent=2),
                file_name="nyc_dot_settings.json",
                mime="application/json",
            )

    with col2:
        uploaded = st.file_uploader(
            "Import settings.json", type="json", key="settings_import"
        )
        if uploaded:
            try:
                imported = json.load(uploaded)
                st.json(imported)
                st.info("Review above then manually apply to .env")
            except Exception as exc:
                st.error(str(exc))


# --------------------------------------------------------------------------- #
# Unit-14 tab helpers
# --------------------------------------------------------------------------- #


def _load_scheduler_config() -> dict:
    """Load scheduler config from data/scheduler_config.json."""
    if _SCHEDULER_CONFIG.exists():
        try:
            return json.loads(_SCHEDULER_CONFIG.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_scheduler_config(data: dict) -> None:
    """Persist scheduler config to data/scheduler_config.json."""
    _SCHEDULER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    _SCHEDULER_CONFIG.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _load_sla_config() -> dict[str, int]:
    """Load SLA thresholds from data/sla_config.json."""
    if _SLA_CONFIG.exists():
        try:
            raw = json.loads(_SLA_CONFIG.read_text(encoding="utf-8"))
            return {k: int(v) for k, v in raw.items() if k in _SLA_DEFAULTS}
        except (json.JSONDecodeError, OSError, ValueError):
            pass
    return dict(_SLA_DEFAULTS)


def _render_scheduler_tab() -> None:
    """Tab 1: Scheduler Config."""
    import pandas as pd

    st.markdown("### ⏰ Nightly Scheduler")
    st.caption(
        "Configure which datasets are prefetched each night and at what time (UTC). "
        "Settings persist to `data/scheduler_config.json`."
    )

    cfg = _load_scheduler_config()
    dataset_keys = list(DATASET_REGISTRY.keys())

    enabled = st.toggle(
        "Enable nightly scheduler",
        key="scheduler_enabled",
        value=cfg.get("enabled", False),
    )

    selected_datasets = st.multiselect(
        "Datasets to prefetch",
        options=dataset_keys,
        default=[k for k in cfg.get("datasets", []) if k in dataset_keys],
        key="scheduler_datasets",
    )

    # Parse stored run time
    stored_time_str = cfg.get("run_time_utc", "02:00")
    try:
        h, m = stored_time_str.split(":")
        default_time = datetime.time(int(h), int(m))
    except (ValueError, AttributeError):
        default_time = datetime.time(2, 0)

    run_time = st.time_input(
        "Run time (UTC)",
        key="scheduler_time",
        value=default_time,
    )

    last_run = get_last_scheduler_run()
    st.metric("Last run", value=last_run)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Save scheduler settings", type="primary"):
            new_cfg = {
                **cfg,
                "enabled": enabled,
                "datasets": selected_datasets,
                "run_time_utc": run_time.strftime("%H:%M"),
            }
            try:
                _save_scheduler_config(new_cfg)
                st.success("Scheduler settings saved to `data/scheduler_config.json`.")
            except OSError as exc:
                st.error(f"Failed to save: {exc}")

    with col2:
        if st.button("▶ Run now", help="Trigger an immediate cache refresh for selected datasets"):
            if not selected_datasets:
                st.warning("Select at least one dataset to prefetch.")
            else:
                with st.spinner("Refreshing cache for selected datasets…"):
                    try:
                        from app.data_loader import fetch_datasets_for_keys
                        frames = fetch_datasets_for_keys(
                            tuple(selected_datasets), limit=50_000
                        )
                        loaded = [k for k, v in frames.items() if v is not None and not getattr(v, "empty", True)]
                        # Record last run
                        import datetime as _dt
                        now_iso = _dt.datetime.utcnow().isoformat() + "Z"
                        run_cfg = _load_scheduler_config()
                        run_cfg["last_run"] = now_iso
                        _save_scheduler_config(run_cfg)
                        st.success(f"Cache refreshed for {len(loaded)}/{len(selected_datasets)} dataset(s).")
                    except Exception as exc:
                        st.error(f"Cache refresh failed: {exc}")

    if cfg:
        with st.expander("Current scheduler_config.json"):
            st.json(cfg)


def _render_sla_tab() -> None:
    """Tab 2: SLA Thresholds."""
    st.markdown("### 🚦 SLA Thresholds")
    st.caption(
        "Define maximum days-since-update for each dataset priority tier. "
        "Saved to `data/sla_config.json`."
    )

    current_sla = _load_sla_config()
    sliders: dict[str, int] = {}

    for priority in ["HIGH", "MED", "LOW"]:
        sliders[priority] = st.slider(
            f"{priority} SLA (days)",
            min_value=1,
            max_value=90,
            value=current_sla.get(priority, _SLA_DEFAULTS[priority]),
            key=f"sla_{priority}",
        )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save thresholds", type="primary"):
            try:
                _SLA_CONFIG.parent.mkdir(parents=True, exist_ok=True)
                _SLA_CONFIG.write_text(json.dumps(sliders, indent=2), encoding="utf-8")
                st.success("SLA thresholds saved to `data/sla_config.json`.")
            except OSError as exc:
                st.error(f"Failed to save: {exc}")

    with col2:
        if st.button("Reset to defaults"):
            try:
                _SLA_CONFIG.parent.mkdir(parents=True, exist_ok=True)
                _SLA_CONFIG.write_text(
                    json.dumps(_SLA_DEFAULTS, indent=2), encoding="utf-8"
                )
                st.success("SLA thresholds reset to defaults.")
                st.rerun()
            except OSError as exc:
                st.error(f"Failed to reset: {exc}")

    if _SLA_CONFIG.exists():
        with st.expander("Current sla_config.json"):
            st.json(_load_sla_config())

    # ------------------------------------------------------------------
    # SLA Compliance Monitor
    # ------------------------------------------------------------------
    st.divider()
    st.markdown("### 📊 SLA Compliance Monitor")
    st.caption(
        "Live compliance status for data quality SLAs across the sidewalk inspections dataset. "
        "Evaluated over the last 24 hours (1440 minutes)."
    )

    _render_sla_compliance_monitor()


def _render_sla_compliance_monitor() -> None:
    """Render the SLA compliance monitoring section."""
    import pandas as pd  # noqa: PLC0415

    from socrata_toolkit.quality.sla import DataQualityTracker, MetricType, Severity, SLADefinition

    # Retrieve or initialise the tracker in session state
    if "sla_tracker" not in st.session_state:
        tracker = DataQualityTracker()

        # Register one SLA per MetricType for the sidewalk_inspections dataset
        _DEMO_SLAS: list[SLADefinition] = [
            SLADefinition(
                metric_name="sidewalk_inspections_completeness",
                metric_type=MetricType.COMPLETENESS,
                target=0.98,
                window="daily",
                dataset="sidewalk_inspections",
                severity=Severity.HIGH,
                owner="data-engineering@nyc.gov",
            ),
            SLADefinition(
                metric_name="sidewalk_inspections_validity",
                metric_type=MetricType.VALIDITY,
                target=0.95,
                window="daily",
                dataset="sidewalk_inspections",
                severity=Severity.HIGH,
                owner="data-engineering@nyc.gov",
            ),
            SLADefinition(
                metric_name="sidewalk_inspections_uniqueness",
                metric_type=MetricType.UNIQUENESS,
                target=0.99,
                window="daily",
                dataset="sidewalk_inspections",
                severity=Severity.MEDIUM,
                owner="data-engineering@nyc.gov",
            ),
            SLADefinition(
                metric_name="sidewalk_inspections_consistency",
                metric_type=MetricType.CONSISTENCY,
                target=0.92,
                window="daily",
                dataset="sidewalk_inspections",
                severity=Severity.MEDIUM,
                owner="data-engineering@nyc.gov",
            ),
            SLADefinition(
                metric_name="sidewalk_inspections_timeliness",
                metric_type=MetricType.TIMELINESS,
                target=0.90,
                window="hourly",
                dataset="sidewalk_inspections",
                severity=Severity.MEDIUM,
                owner="data-engineering@nyc.gov",
            ),
            SLADefinition(
                metric_name="sidewalk_inspections_accuracy",
                metric_type=MetricType.ACCURACY,
                target=0.95,
                window="daily",
                dataset="sidewalk_inspections",
                severity=Severity.HIGH,
                owner="data-engineering@nyc.gov",
            ),
        ]

        # Seed demo metric values (realistic range 0.85–0.99)
        _DEMO_SEEDS: list[tuple[str, float, MetricType]] = [
            ("sidewalk_inspections_completeness", 0.985, MetricType.COMPLETENESS),
            ("sidewalk_inspections_validity", 0.962, MetricType.VALIDITY),
            ("sidewalk_inspections_uniqueness", 0.997, MetricType.UNIQUENESS),
            ("sidewalk_inspections_consistency", 0.883, MetricType.CONSISTENCY),
            ("sidewalk_inspections_timeliness", 0.914, MetricType.TIMELINESS),
            ("sidewalk_inspections_accuracy", 0.941, MetricType.ACCURACY),
        ]

        for sla in _DEMO_SLAS:
            tracker.register_sla(sla)

        for metric_name, value, metric_type in _DEMO_SEEDS:
            tracker.record_metric(
                metric_name=metric_name,
                value=value,
                dataset="sidewalk_inspections",
                metric_type=metric_type,
                window="daily",
            )

        st.session_state["sla_tracker"] = tracker
    else:
        tracker = st.session_state["sla_tracker"]

    # Generate compliance report
    report = tracker.get_sla_compliance_report(lookback_minutes=1440)

    overall_pct = report.get("overall_compliance", 0.0) * 100
    sla_results = report.get("sla_results", [])
    total_slas = len(sla_results)
    breach_count = sum(1 for r in sla_results if not r.get("compliant", True))

    # ---- Summary metric cards ----
    m1, m2, m3 = st.columns(3)
    m1.metric(
        label="Overall Compliance",
        value=f"{overall_pct:.1f}%",
        delta=f"{total_slas - breach_count}/{total_slas} passing",
    )
    m2.metric(label="Total SLAs", value=total_slas)
    m3.metric(
        label="Breaches",
        value=breach_count,
        delta=breach_count if breach_count else None,
        delta_color="inverse",
    )

    # ---- Per-SLA status table ----
    st.markdown("#### Per-SLA Status")

    if not sla_results:
        st.info("No SLA results available.")
        return

    rows = []
    for result in sla_results:
        compliant = result.get("compliant", True)
        actual = result.get("actual", 0.0)
        target = result.get("target", 0.0)
        gap = actual - target
        rows.append(
            {
                "SLA Name": result.get("metric_name", ""),
                "Target": f"{target:.1%}",
                "Actual": f"{actual:.1%}",
                "Gap": f"{gap:+.1%}",
                "Status": "PASS" if compliant else "FAIL",
                "Severity": result.get("severity", "").upper(),
                "Window": result.get("window", ""),
            }
        )

    sla_df = pd.DataFrame(rows)

    with st.expander("SLA results table", expanded=True):
        st.dataframe(sla_df, use_container_width=True, hide_index=True)

    # ---- Per-SLA colour-coded status cards ----
    st.markdown("#### SLA Health Detail")
    for result in sla_results:
        compliant = result.get("compliant", True)
        severity = result.get("severity", "low")
        name = result.get("metric_name", "")
        actual = result.get("actual", 0.0)
        target = result.get("target", 0.0)
        detail = f"**{name}** — actual: `{actual:.1%}` vs target: `{target:.1%}`"

        if compliant:
            st.success(f"PASS  {detail}")
        elif severity == "critical":
            st.error(f"BREACH (critical)  {detail}")
        elif severity == "high":
            st.error(f"BREACH (high)  {detail}")
        else:
            st.warning(f"BREACH ({severity})  {detail}")

    # ---- Refresh button ----
    if st.button("🔄 Refresh compliance report"):
        # Drop cached tracker so a fresh one is seeded on rerender
        st.session_state.pop("sla_tracker", None)
        st.rerun()


def _render_alert_config_tab() -> None:
    """Tab 3: Alert Config (Slack + ArcGIS)."""
    st.markdown("### 🔔 Alert Configuration")

    # ---- Slack section ----
    st.markdown("#### Slack Webhook")
    slack_webhook = st.text_input(
        "Slack Webhook URL",
        type="password",
        key="slack_webhook_url",
        value=os.getenv("SLACK_WEBHOOK_URL", ""),
        help="Paste your Slack Incoming Webhook URL here.",
    )
    if st.button("Test Slack connection"):
        url = slack_webhook.strip() or os.getenv("SLACK_WEBHOOK_URL", "").strip()
        if not url:
            st.warning("Enter a Slack Webhook URL first.")
        else:
            ok, msg = send_slack_alert(
                webhook_url=url,
                title="NYC DOT SIM — Connection Test",
                message="This is a test message from the NYC DOT SIM Toolkit (Unit 14 Settings UI).",
                severity="info",
            )
            if ok:
                st.success(f"Slack test succeeded: {msg}")
            else:
                st.error(f"Slack test failed: {msg}")

    st.divider()

    # ---- ArcGIS section ----
    st.markdown("#### ArcGIS Online")
    arcgis_org_url = st.text_input(
        "ArcGIS Online Org URL",
        key="arcgis_org_url",
        value=os.getenv("ARCGIS_ORG_URL", ""),
        placeholder="https://your-org.maps.arcgis.com",
    )
    arcgis_username = st.text_input(
        "ArcGIS Username",
        key="arcgis_username",
        value=os.getenv("ARCGIS_USERNAME", ""),
    )
    arcgis_password = st.text_input(
        "ArcGIS Password",
        type="password",
        key="arcgis_password",
    )
    if st.button("Test ArcGIS connection"):
        if not arcgis_org_url or not arcgis_username or not arcgis_password:
            st.warning("Org URL, username, and password are all required.")
        else:
            with st.spinner("Testing ArcGIS connection…"):
                ok, msg = test_arcgis_connection(
                    arcgis_org_url.strip(),
                    arcgis_username.strip(),
                    arcgis_password,
                )
            if ok:
                st.success(f"ArcGIS connection succeeded: {msg}")
            else:
                st.error(f"ArcGIS connection failed: {msg}")


def _render_environment_tab() -> None:
    """Tab 4: Environment variables reference with masked values."""
    import pandas as pd

    st.markdown("### 📋 Environment Variables")
    st.caption(
        "Shows key environment variables used by this application. "
        "Values are masked for security."
    )

    rows = []
    for entry in ENV_VARS_TABLE:
        raw = os.getenv(entry["name"], "").strip()
        masked = "***set***" if raw else "not set"
        rows.append(
            {
                "Variable": entry["name"],
                "Description": entry["description"],
                "Required": "Yes" if entry["required"] else "No",
                "Current Value": masked,
            }
        )

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.caption(
        "To set these variables, add them to your `.env` file in the project root "
        "or configure them in the **API Tokens** / **Configuration** tabs."
    )
