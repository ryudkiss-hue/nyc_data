"""Data Quality Dashboard view — reconciliation, validation results, audit trail.

Provides analysts with comprehensive visibility into data quality metrics,
including row count reconciliation, validation results, and access audit logs.

Standards: Python 3.9+, type hints, comprehensive docstrings, operational logging
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from socrata_toolkit.core.duckdb_store import query_parquet_cache
from socrata_toolkit.governance.core import AuditLogger
from socrata_toolkit.quality.reconciliation import DataReconciliation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cached data fetchers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600)
def get_actual_counts() -> dict[str, int]:
    """Fetch actual row counts from DuckDB cache.

    Returns:
        Dict mapping table keys to row counts
    """
    counts = {}
    tables = [
        "inspection",
        "violations",
        "dismissals",
        "built",
        "lot_info",
        "reinspection",
        "tree_damage",
        "correspondences",
        "curb_metal_protruding",
        "ramp_locations",
        "ramp_complaints",
        "ramp_progress",
        "street_permits",
        "weekly_construction",
        "capital_intersections",
        "street_construction_inspections",
        "street_closures_block",
        "street_resurfacing_schedule",
        "street_resurfacing_inhouse",
        "step_streets",
        "sidewalk_planimetric",
        "pedestrian_demand",
        "mappluto",
        "complaints_311",
    ]

    for table_key in tables:
        try:
            df = query_parquet_cache(table_key)
            counts[table_key] = len(df)
            logger.debug(f"Row count for {table_key}: {len(df)}")
        except (FileNotFoundError, RuntimeError, Exception) as e:
            logger.debug(f"Could not fetch {table_key}: {e}")
            counts[table_key] = 0

    return counts

@st.cache_data(ttl=3600)
def get_expected_counts() -> dict[str, int]:
    """Fetch expected row counts from dataset registry.

    Expected counts come from CLAUDE.md dataset registry.
    These are baseline/SLA targets for comparison.

    Returns:
        Dict mapping table keys to expected row counts
    """
    # From CLAUDE.md Dataset Registry (item 19)
    return {
        "inspection": 398_000,
        "violations": 312_000,
        "dismissals": 85_000,
        "built": 105_000,
        "lot_info": 1_200_000,
        "reinspection": 36_000,
        "tree_damage": 17_000,
        "correspondences": 30_000,
        "curb_metal_protruding": 23_000,
        "ramp_locations": 217_000,
        "ramp_complaints": 6_000,
        "ramp_progress": 187_000,
        "street_permits": 3_600_000,
        "weekly_construction": 75,
        "capital_intersections": 7_800,
        "street_construction_inspections": 11_500_000,
        "street_closures_block": 4_300,
        "street_resurfacing_schedule": 309_000,
        "street_resurfacing_inhouse": 602_000,
        "step_streets": 110,
        "sidewalk_planimetric": 50_000,
        "pedestrian_demand": 127_000,
        "mappluto": 858_000,
        "complaints_311": 21_300_000,
    }

@st.cache_data(ttl=1800)
def fetch_audit_logs(days: int = 7) -> list[dict[str, Any]]:
    """Fetch audit trail from local storage (last N days).

    Args:
        days: Number of days of audit history to retrieve

    Returns:
        List of audit event dictionaries
    """
    audit_path = Path("data") / "audit_logs.json"
    if not audit_path.exists():
        return []

    try:
        import json

        all_events = json.loads(audit_path.read_text(encoding="utf-8"))

        # Filter to last N days
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        filtered = []
        for event in all_events:
            try:
                event_ts = datetime.fromisoformat(
                    event.get("timestamp", "").replace("Z", "+00:00")
                )
                if event_ts >= cutoff:
                    filtered.append(event)
            except (ValueError, AttributeError):
                pass

        return sorted(filtered, key=lambda e: e.get("timestamp", ""), reverse=True)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        logger.warning(f"Could not load audit logs: {e}")
        return []

@st.cache_data(ttl=300)
def fetch_validation_results() -> dict[str, Any]:
    """Fetch recent validation results.

    Returns:
        Dict with validation summary and detailed results
    """
    validation_path = Path("data") / "validation_results.json"
    if not validation_path.exists():
        return {
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "details": [],
        }

    try:
        import json

        return json.loads(validation_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "details": [],
        }

# ---------------------------------------------------------------------------
# Streamlit UI functions
# ---------------------------------------------------------------------------

def render_data_quality_page() -> None:
    """Render the data quality dashboard with 3 tabs.

    Tabs:
    1. Reconciliation — row count discrepancies
    2. Validation Results — data quality validation checks
    3. Audit Trail — access logs and governance events
    """
    st.title("Data Quality Dashboard")
    st.markdown(
        "Monitor data reconciliation, validation results, and audit trails "
        "to ensure data quality and governance compliance."
    )

    # Create tabs
    tab1, tab2, tab3 = st.tabs(
        ["Reconciliation", "Validation Results", "Audit Trail"]
    )

    # ---------------------------------------------------------------------------
    # TAB 1: RECONCILIATION
    # ---------------------------------------------------------------------------
    with tab1:
        st.header("Reconciliation")
        st.markdown("Compare expected vs actual row counts across core datasets.")

        # Fetch data
        expected = get_expected_counts()
        actual = get_actual_counts()

        # Run reconciliation
        recon = DataReconciliation("NYC DOT Datasets", expected, actual)
        results = recon.check_counts(tolerance_pct=0.05)

        # Display summary metrics
        summary = recon.summary_stats()
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Tables", summary["total_checks"])

        with col2:
            st.metric(
                "OK",
                summary["ok_count"],
                delta=f"{summary['ok_pct']:.1f}%",
                delta_color="normal",
            )

        with col3:
            st.metric(
                "Warnings",
                summary["warning_count"],
                delta=f"{summary['warning_pct']:.1f}%",
                delta_color="inverse",
            )

        with col4:
            st.metric(
                "Failed",
                summary["fail_count"],
                delta=f"{summary['fail_pct']:.1f}%",
                delta_color="inverse",
            )

        st.divider()

        # Reconciliation table
        st.subheader("Detailed Results")
        df_results = pd.DataFrame([r.to_dict() for r in results])

        # Format display
        if not df_results.empty:
            df_display = df_results[[
                "table",
                "expected",
                "actual",
                "variance",
                "variance_pct",
                "status",
            ]].copy()
            df_display["expected"] = df_display["expected"].apply(lambda x: f"{x:,}")
            df_display["actual"] = df_display["actual"].apply(lambda x: f"{x:,}")
            df_display["variance"] = df_display["variance"].apply(lambda x: f"{x:+,}")
            df_display["variance_pct"] = df_display["variance_pct"].apply(
                lambda x: f"{x:+.2f}%"
            )

            # Color-code by status
            def highlight_status(val):
                if val == "OK":
                    return "color: green"
                elif val == "WARNING":
                    return "color: orange"
                else:
                    return "color: red"

            styled_df = df_display.style.applymap(
                highlight_status, subset=["status"]
            )
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

        # Discrepancies section
        discrepancies = [r for r in results if r.status != "OK"]
        if discrepancies:
            st.subheader("Discrepancies Requiring Attention")
            for disc in sorted(
                discrepancies, key=lambda r: abs(r.variance_pct), reverse=True
            ):
                with st.expander(
                    f"**{disc.table}** — {disc.status} ({disc.variance_pct:+.2f}%)"
                ):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Expected", f"{disc.expected:,}")
                    with col2:
                        st.metric("Actual", f"{disc.actual:,}")
                    with col3:
                        st.metric("Variance", f"{disc.variance:+,}")
                    with col4:
                        st.metric("Percent", f"{disc.variance_pct:+.2f}%")

        st.divider()

        # Download report button
        st.subheader("Export Report")
        report_text = recon.generate_reconciliation_report()
        st.download_button(
            label="Download Reconciliation Report (TXT)",
            data=report_text,
            file_name="reconciliation_report.txt",
            mime="text/plain",
        )

    # ---------------------------------------------------------------------------
    # TAB 2: VALIDATION RESULTS
    # ---------------------------------------------------------------------------
    with tab2:
        st.header("Validation Results")
        st.markdown("Data quality validation checks and summary.")

        # Fetch validation results
        validation_data = fetch_validation_results()

        # Summary metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Passed", validation_data.get("passed", 0))

        with col2:
            st.metric("Warnings", validation_data.get("warnings", 0))

        with col3:
            st.metric("Failed", validation_data.get("failed", 0))

        st.divider()

        # Validation details
        details = validation_data.get("details", [])
        if details:
            st.subheader("Validation Details")
            df_validation = pd.DataFrame(details)

            # Show in table format
            if "status" in df_validation.columns:

                def highlight_validation_status(val):
                    if val == "PASS":
                        return "color: green"
                    elif val == "WARNING":
                        return "color: orange"
                    else:
                        return "color: red"

                styled_val = df_validation.style.applymap(
                    highlight_validation_status, subset=["status"]
                )
                st.dataframe(styled_val, use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_validation, use_container_width=True, hide_index=True)
        else:
            st.info("No validation results available yet.")

    # ---------------------------------------------------------------------------
    # TAB 3: AUDIT TRAIL
    # ---------------------------------------------------------------------------
    with tab3:
        st.header("Audit Trail")
        st.markdown("Access logs and governance events from the last 7 days.")

        # Fetch audit logs
        audit_events = fetch_audit_logs(days=7)

        if audit_events:
            # Summary
            col1, col2, col3, col4 = st.columns(4)

            read_count = sum(
                1 for e in audit_events if e.get("action", "").lower() == "read"
            )
            write_count = sum(
                1 for e in audit_events if e.get("action", "").lower() == "write"
            )
            export_count = sum(
                1 for e in audit_events if e.get("action", "").lower() == "export"
            )
            unique_actors = len(set(e.get("actor", "") for e in audit_events))

            with col1:
                st.metric("Read Events", read_count)
            with col2:
                st.metric("Write Events", write_count)
            with col3:
                st.metric("Export Events", export_count)
            with col4:
                st.metric("Unique Users", unique_actors)

            st.divider()

            # Audit log table
            st.subheader("Recent Events")
            df_audit = pd.DataFrame(audit_events)

            # Select relevant columns
            display_cols = [
                col for col in ["timestamp", "actor", "action", "resource"]
                if col in df_audit.columns
            ]
            if display_cols:
                st.dataframe(
                    df_audit[display_cols], use_container_width=True, hide_index=True
                )

            st.divider()

            # Action summary chart
            st.subheader("Events by Action")
            action_counts = df_audit["action"].value_counts()
            st.bar_chart(action_counts)
        else:
            st.info("No audit events in the last 7 days.")
