"""Settings, readiness, completeness, health, cache management, and API configuration."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import streamlit as st

from app.data_loader import cache_freshness_report
from app.services import agency
from app.ui.theme import render_quality_badge, render_readiness_bars
from app.utils.i18n import t
from socrata_toolkit.core.readiness import run_readiness_checks

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _REPO_ROOT / ".env"
_PRESETS_FILE = _REPO_ROOT / "data" / "filter_presets.json"


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
