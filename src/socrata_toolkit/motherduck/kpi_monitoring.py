"""KPI Analytics Monitoring & Alerting.

Monitors computation status, data freshness, and SLA breaches.
Sends alerts via Slack webhook.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

import duckdb
import requests

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """An alert to be sent."""
    severity: str  # INFO, WARNING, ERROR
    title: str
    message: str
    details: Optional[dict] = None


class SlackNotifier:
    """Send alerts to Slack channel."""

    def __init__(self, webhook_url: str):
        """Initialize with Slack webhook URL."""
        self.webhook_url = webhook_url

    def send_alert(self, alert: Alert) -> bool:
        """Send alert to Slack. Returns True if successful."""
        if not self.webhook_url:
            logger.warning("Slack webhook URL not set; skipping notification")
            return False

        color_map = {
            "INFO": "#36a64f",  # Green
            "WARNING": "#ff9f43",  # Orange
            "ERROR": "#ee5a6f",  # Red
        }

        payload = {
            "attachments": [
                {
                    "color": color_map.get(alert.severity, "#999999"),
                    "title": alert.title,
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity,
                            "short": True
                        },
                    ],
                    "footer": "KPI Analytics Monitoring",
                    "ts": int(__import__("time").time()),
                }
            ]
        }

        if alert.details:
            for key, value in alert.details.items():
                payload["attachments"][0]["fields"].append({
                    "title": key,
                    "value": str(value),
                    "short": True
                })

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Alert sent to Slack: {alert.title}")
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {str(e)}")
            return False


class KPIMonitor:
    """Monitor KPI analytics pipeline health."""

    def __init__(self, conn: duckdb.DuckDBPyConnection, slack_webhook: Optional[str] = None):
        """Initialize monitor with database connection and optional Slack."""
        self.conn = conn
        self.notifier = SlackNotifier(slack_webhook) if slack_webhook else None

    def check_computation_status(self) -> Optional[Alert]:
        """Check if last computation succeeded."""
        try:
            result = self.conn.execute(
                """
                SELECT
                  computation_status,
                  COUNT(*) as count
                FROM analytics.kpi_statistics_by_borough
                GROUP BY computation_status
                """
            ).fetchall()

            if not result:
                return Alert(
                    severity="WARNING",
                    title="No computation status found",
                    message="Analytics layer appears empty"
                )

            failed = [r for r in result if r[0] == "FAILED"]
            if failed:
                return Alert(
                    severity="ERROR",
                    title="KPI Computation Failed",
                    message=f"{failed[0][1]} rows failed computation",
                    details={"Status": "FAILED", "Rows": failed[0][1]}
                )

            partial = [r for r in result if r[0] == "PARTIAL"]
            if partial:
                return Alert(
                    severity="WARNING",
                    title="Partial KPI Computation",
                    message=f"{partial[0][1]} rows completed partially",
                    details={"Status": "PARTIAL", "Rows": partial[0][1]}
                )

            return None

        except Exception as e:
            return Alert(
                severity="ERROR",
                title="Computation Status Check Failed",
                message=f"Unable to check status: {str(e)}"
            )

    def check_data_freshness(self, max_age_minutes: int = 30) -> Optional[Alert]:
        """Check if data is stale."""
        try:
            result = self.conn.execute(
                """
                SELECT
                  MAX(analytics_timestamp) as latest,
                  DATEDIFF('minutes', MAX(analytics_timestamp), CURRENT_TIMESTAMP) as minutes_ago
                FROM analytics.kpi_statistics_by_borough
                """
            ).fetchone()

            if not result or result[0] is None:
                return Alert(
                    severity="ERROR",
                    title="No analytics data found",
                    message="Analytics layer is empty"
                )

            minutes_ago = result[1]
            if minutes_ago > max_age_minutes:
                return Alert(
                    severity="WARNING",
                    title="Stale KPI Analytics Data",
                    message=f"Data is {minutes_ago} minutes old (threshold: {max_age_minutes} min)",
                    details={
                        "Latest Timestamp": str(result[0]),
                        "Age (minutes)": minutes_ago,
                        "Threshold (minutes)": max_age_minutes
                    }
                )

            return None

        except Exception as e:
            return Alert(
                severity="ERROR",
                title="Freshness Check Failed",
                message=f"Unable to check freshness: {str(e)}"
            )

    def check_sla_breaches(self, breach_threshold: float = 50.0) -> Optional[Alert]:
        """Check for KPIs with high SLA breach probability."""
        try:
            result = self.conn.execute(
                """
                SELECT
                  kpi_name,
                  borough,
                  pct_exceeding_risk_threshold
                FROM analytics.kpi_statistics_by_borough
                WHERE pct_exceeding_risk_threshold > ?
                ORDER BY pct_exceeding_risk_threshold DESC
                LIMIT 5
                """,
                (breach_threshold,)
            ).fetchall()

            if not result:
                return None

            kpi_list = [f"{r[0]} ({r[1]}): {r[2]:.1f}%" for r in result]

            return Alert(
                severity="WARNING",
                title="SLA Breach Risk Detected",
                message=f"{len(result)} KPI-borough pairs exceed {breach_threshold}% risk threshold",
                details={"At-Risk KPIs": "\n".join(kpi_list[:3])}
            )

        except Exception as e:
            return Alert(
                severity="ERROR",
                title="SLA Check Failed",
                message=f"Unable to check SLA: {str(e)}"
            )

    def check_data_anomalies(self) -> Optional[Alert]:
        """Check for data quality anomalies."""
        try:
            result = self.conn.execute(
                """
                SELECT
                  COUNT(*) as anomaly_count,
                  COUNT(CASE WHEN outlier_count_3sd > n * 0.1 THEN 1 END) as high_outlier_count,
                  COUNT(CASE WHEN coeff_variation > 100 THEN 1 END) as extreme_cv_count
                FROM analytics.kpi_statistics_by_borough
                """
            ).fetchone()

            if not result:
                return None

            anomaly_count, high_outliers, extreme_cv = result

            if anomaly_count > 10:
                return Alert(
                    severity="WARNING",
                    title="Data Quality Anomalies Detected",
                    message=f"{anomaly_count} anomalies found across KPI-borough pairs",
                    details={
                        "High Outlier Count (>10%)": high_outliers,
                        "Extreme CV (>100%)": extreme_cv
                    }
                )

            return None

        except Exception as e:
            return Alert(
                severity="ERROR",
                title="Anomaly Check Failed",
                message=f"Unable to check anomalies: {str(e)}"
            )

    def monitor_all(self) -> list[Alert]:
        """Run all checks and return list of alerts."""
        alerts = []

        checks = [
            ("Computation Status", self.check_computation_status),
            ("Data Freshness", self.check_data_freshness),
            ("SLA Breaches", self.check_sla_breaches),
            ("Data Anomalies", self.check_data_anomalies),
        ]

        for check_name, check_fn in checks:
            try:
                alert = check_fn()
                if alert:
                    alerts.append(alert)
                    logger.warning(f"{check_name}: {alert.title}")
                    if self.notifier:
                        self.notifier.send_alert(alert)
            except Exception as e:
                logger.error(f"{check_name} check failed: {str(e)}")

        return alerts

    def log_monitoring_result(self, alerts: list[Alert]) -> None:
        """Log monitoring results to a monitoring table."""
        try:
            # Create monitoring table if it doesn't exist
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analytics.monitoring_log (
                    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    severity VARCHAR,
                    check_name VARCHAR,
                    message VARCHAR,
                    details VARCHAR
                )
                """
            )

            # Log each alert
            for alert in alerts:
                self.conn.execute(
                    """
                    INSERT INTO analytics.monitoring_log (severity, check_name, message, details)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        alert.severity,
                        alert.title,
                        alert.message,
                        json.dumps(alert.details) if alert.details else None
                    )
                )

            logger.info(f"Logged {len(alerts)} alerts to monitoring table")

        except Exception as e:
            logger.error(f"Failed to log monitoring results: {str(e)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Example usage
    import os
    conn = duckdb.connect("md:", config={"motherduck_token": os.getenv("MOTHERDUCK_TOKEN")})
    slack_url = os.getenv("SLACK_WEBHOOK_URL")

    monitor = KPIMonitor(conn, slack_url)
    alerts = monitor.monitor_all()

    if alerts:
        print(f"\n⚠️  {len(alerts)} alerts found:")
        for alert in alerts:
            print(f"  [{alert.severity}] {alert.title}: {alert.message}")
    else:
        print("\n✅ All checks passed!")

    monitor.log_monitoring_result(alerts)
