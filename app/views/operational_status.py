"""Operational Status Dashboard — Real-time alerts and monitoring.

Displays current alerts, alert history, and severity distribution for the data
operations team. Provides alert acknowledgement and resolution actions.

Features:
- Real-time alert summary by severity
- Alert history with filters
- Alert timeline visualization
- Alert acknowledgement/resolution actions
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import streamlit as st

logger = logging.getLogger(__name__)

def render_operational_status_page() -> None:
    """Render the operational status dashboard.

    Displays:
    - Current active alerts by severity (HIGH, MEDIUM, LOW)
    - Alert history table with sorting and filtering
    - Alert timeline chart
    - Alert summary statistics
    """
    st.set_page_config(page_title="Operational Status", layout="wide")

    st.markdown("# 📊 Operational Status")
    st.markdown(
        "Real-time monitoring of data quality alerts. Track freshness, validation, "
        "reconciliation, and domain rule breaches."
    )

    # Get or initialize alert manager in session state
    if "alert_manager" not in st.session_state:
        from socrata_toolkit.observability import AlertManager
        st.session_state.alert_manager = AlertManager()
        logger.info("AlertManager initialized in session state")

    alert_manager = st.session_state.alert_manager

    # =========================================================================
    # Section 1: Current Alerts Summary
    # =========================================================================
    st.markdown("## Current Alerts")

    col1, col2, col3, col4 = st.columns(4)

    alert_summary = alert_manager.get_alert_summary()
    active_alerts = alert_manager.get_active_alerts()

    with col1:
        st.metric(
            "Active Alerts",
            len(active_alerts),
            delta=None,
            help="New and Acknowledged alerts",
        )

    with col2:
        st.metric(
            "🔴 HIGH",
            alert_summary["HIGH"],
            delta=None,
            help="High severity alerts",
        )

    with col3:
        st.metric(
            "🟡 MEDIUM",
            alert_summary["MEDIUM"],
            delta=None,
            help="Medium severity alerts",
        )

    with col4:
        st.metric(
            "🟢 LOW",
            alert_summary["LOW"],
            delta=None,
            help="Low severity alerts",
        )

    st.divider()

    # =========================================================================
    # Section 2: Alert List with Actions
    # =========================================================================
    if active_alerts:
        st.markdown("### Current Alerts")

        # Create a table of active alerts
        for alert in sorted(active_alerts, key=lambda a: a.timestamp, reverse=True):
            col_severity, col_message, col_actions = st.columns([1, 3, 1])

            # Severity badge
            with col_severity:
                if alert.severity.value == "HIGH":
                    st.markdown("🔴 **HIGH**")
                elif alert.severity.value == "MEDIUM":
                    st.markdown("🟡 **MEDIUM**")
                else:
                    st.markdown("🟢 **LOW**")

            # Alert message and details
            with col_message:
                st.markdown(f"**{alert.check_name}** ({alert.dataset_name})")
                st.markdown(f"*{alert.message}*")
                st.caption(
                    f"Type: {alert.alert_type} | Status: {alert.status.value} | "
                    f"ID: {alert.alert_id[:8]}..."
                )

            # Action buttons
            with col_actions:
                col_ack, col_res = st.columns(2)
                with col_ack:
                    if st.button("✓ Ack", key=f"ack_{alert.alert_id}", help="Acknowledge"):
                        alert_manager.acknowledge_alert(alert.alert_id)
                        st.rerun()

                with col_res:
                    if st.button("✕ Resolve", key=f"res_{alert.alert_id}", help="Resolve"):
                        alert_manager.resolve_alert(alert.alert_id)
                        st.rerun()

            st.divider()
    else:
        st.info("✓ No active alerts. All systems operating normally.")

    # =========================================================================
    # Section 3: Alert History
    # =========================================================================
    st.markdown("## Alert History")

    # Filters
    col_filter1, col_filter2, col_filter3 = st.columns(3)

    with col_filter1:
        severity_filter = st.multiselect(
            "Severity",
            ["HIGH", "MEDIUM", "LOW"],
            default=["HIGH", "MEDIUM", "LOW"],
            help="Filter by severity level",
        )

    with col_filter2:
        alert_type_filter = st.multiselect(
            "Alert Type",
            [
                "data_freshness",
                "validation_failures",
                "row_count_anomaly",
                "reconciliation_discrepancy",
                "domain_rule_breach",
            ],
            help="Filter by check type",
        )

    with col_filter3:
        hours_lookback = st.selectbox(
            "Time Range",
            [1, 6, 24, 72, 168],
            format_func=lambda h: f"Last {h}h" if h < 24 else f"Last {h//24}d",
            help="Alert history lookback period",
        )

    # Build alert history dataframe
    import pandas as pd

    history_records = []
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_lookback)

    for alert_dict in alert_manager.alert_history:
        alert_time = datetime.fromisoformat(
            alert_dict["timestamp"].replace("Z", "+00:00")
        )
        if alert_time < cutoff_time:
            continue

        # Apply filters
        if alert_dict["severity"] not in severity_filter:
            continue
        if alert_type_filter and alert_dict["alert_type"] not in alert_type_filter:
            continue

        history_records.append({
            "Timestamp": alert_time.strftime("%Y-%m-%d %H:%M:%S"),
            "Severity": alert_dict["severity"],
            "Check": alert_dict["check_name"],
            "Dataset": alert_dict["dataset_name"],
            "Message": alert_dict["message"],
            "Status": alert_dict.get("status", "unknown"),
        })

    if history_records:
        history_df = pd.DataFrame(history_records)
        st.dataframe(
            history_df,
            use_container_width=True,
            height=300,
            hide_index=True,
        )
    else:
        st.info("No alerts in selected time range.")

    # =========================================================================
    # Section 4: Alert Distribution
    # =========================================================================
    st.markdown("## Alert Distribution")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("### By Severity")
        if history_records:
            severity_counts = {}
            for record in history_records:
                sev = record["Severity"]
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

            import plotly.graph_objects as go

            fig = go.Figure(
                data=[
                    go.Bar(
                        x=list(severity_counts.keys()),
                        y=list(severity_counts.values()),
                        marker_color=["#d62728", "#ff7f0e", "#2ca02c"],
                    )
                ]
            )
            fig.update_layout(
                title="Alerts by Severity",
                xaxis_title="Severity",
                yaxis_title="Count",
                height=350,
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data to display")

    with col_chart2:
        st.markdown("### By Check Type")
        if history_records:
            check_counts = {}
            for record in history_records:
                check = record["Check"]
                check_counts[check] = check_counts.get(check, 0) + 1

            import plotly.graph_objects as go

            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=list(check_counts.keys()),
                        values=list(check_counts.values()),
                    )
                ]
            )
            fig.update_layout(
                title="Alerts by Check Type",
                height=350,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data to display")

    # =========================================================================
    # Section 5: Alert Statistics
    # =========================================================================
    st.markdown("## Statistics")

    stats_col1, stats_col2, stats_col3 = st.columns(3)

    with stats_col1:
        total_alerts = len(alert_manager.alert_history)
        st.metric("Total Alerts (All Time)", total_alerts)

    with stats_col2:
        resolved_count = sum(
            1 for a in alert_manager.alert_history if a.get("status") == "resolved"
        )
        st.metric("Resolved", resolved_count)

    with stats_col3:
        if total_alerts > 0:
            resolution_rate = (resolved_count / total_alerts * 100)
        else:
            resolution_rate = 0
        st.metric("Resolution Rate", f"{resolution_rate:.1f}%")

    st.divider()

    # Debug info (collapse-able)
    with st.expander("Debug Info"):
        st.write(f"Alert Manager State: {len(alert_manager.alerts)} tracked alerts")
        st.write(f"Alert History: {len(alert_manager.alert_history)} total events")
        st.write(f"Notification Handlers: {len(alert_manager.notification_handlers)} registered")

if __name__ == "__main__":
    render_operational_status_page()
