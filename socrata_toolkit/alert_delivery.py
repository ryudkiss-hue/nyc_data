"""Alert Delivery -- glue connecting notification rules to actual delivery channels.

Bridges the notification rules engine with Teams webhooks, email (SMTP),
and Slack webhooks for real-time alert delivery.

Configure via environment variables:
- TEAMS_WEBHOOK_URL: Microsoft Teams incoming webhook
- SLACK_WEBHOOK_URL: Slack incoming webhook
- SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM, ALERT_RECIPIENTS

Example::

    from socrata_toolkit.alert_delivery import deliver_alerts
    from socrata_toolkit.notification_rules import RulesEngine, Rule

    engine = RulesEngine()
    engine.add_rule(Rule("backlog", field="pending", operator=">", threshold=100))
    alerts = engine.evaluate({"pending": 150})
    deliver_alerts(alerts)  # sends to all configured channels
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import requests as _requests

from .notification_rules import RuleAlert

log = logging.getLogger(__name__)


def deliver_alerts(
    alerts: List[RuleAlert],
    channels: Optional[List[str]] = None,
) -> Dict[str, int]:
    """Deliver alerts to all configured channels.

    Auto-detects channels from environment variables unless explicitly specified.

    Args:
        alerts: List of RuleAlert objects to deliver.
        channels: Override channel list. Default: auto-detect from env vars.

    Returns:
        Dict mapping channel name to count of successfully delivered alerts.
    """
    if not alerts:
        return {}

    available = channels or _detect_channels()
    results: Dict[str, int] = {}

    for channel in available:
        count = 0
        for alert in alerts:
            try:
                if channel == "teams":
                    _send_teams(alert)
                    count += 1
                elif channel == "slack":
                    _send_slack(alert)
                    count += 1
                elif channel == "email":
                    _send_email(alert)
                    count += 1
                elif channel == "log":
                    _send_log(alert)
                    count += 1
            except Exception as exc:
                log.warning("Failed to deliver alert '%s' via %s: %s", alert.rule_name, channel, exc)
        results[channel] = count

    return results


def _detect_channels() -> List[str]:
    """Auto-detect available delivery channels from environment."""
    channels = ["log"]  # always available
    if os.getenv("TEAMS_WEBHOOK_URL"):
        channels.append("teams")
    if os.getenv("SLACK_WEBHOOK_URL"):
        channels.append("slack")
    if os.getenv("SMTP_HOST") and os.getenv("ALERT_RECIPIENTS"):
        channels.append("email")
    return channels


def _send_teams(alert: RuleAlert) -> None:
    """Send alert to Microsoft Teams via incoming webhook."""
    url = os.environ["TEAMS_WEBHOOK_URL"]
    color = {"critical": "FF0000", "warning": "FFC107", "info": "0078D4"}.get(alert.severity, "6C757D")
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": color,
        "summary": f"[{alert.severity.upper()}] {alert.rule_name}",
        "sections": [{
            "activityTitle": f"[{alert.severity.upper()}] {alert.rule_name}",
            "text": alert.message,
            "facts": [
                {"name": "Field", "value": alert.field},
                {"name": "Value", "value": str(alert.actual_value)},
                {"name": "Threshold", "value": str(alert.threshold)},
                {"name": "Time", "value": alert.timestamp},
            ],
        }],
    }
    _requests.post(url, json=payload, timeout=10)


def _send_slack(alert: RuleAlert) -> None:
    """Send alert to Slack via incoming webhook."""
    url = os.environ["SLACK_WEBHOOK_URL"]
    emoji = {"critical": ":rotating_light:", "warning": ":warning:", "info": ":information_source:"}.get(alert.severity, ":bell:")
    payload = {
        "text": f"{emoji} *[{alert.severity.upper()}] {alert.rule_name}*\n{alert.message}\n`{alert.field}: {alert.actual_value} (threshold: {alert.threshold})`",
    }
    _requests.post(url, json=payload, timeout=10)


def _send_email(alert: RuleAlert) -> None:
    """Send alert via SMTP."""
    import smtplib
    from email.message import EmailMessage

    host = os.environ["SMTP_HOST"]
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASS", "")
    from_addr = os.getenv("SMTP_FROM", user)
    recipients = os.environ["ALERT_RECIPIENTS"].split(",")

    msg = EmailMessage()
    msg["Subject"] = f"[{alert.severity.upper()}] DOT Alert: {alert.rule_name}"
    msg["From"] = from_addr
    msg["To"] = ", ".join(recipients)
    msg.set_content(
        f"Alert: {alert.rule_name}\n"
        f"Severity: {alert.severity}\n"
        f"Message: {alert.message}\n"
        f"Field: {alert.field}\n"
        f"Value: {alert.actual_value}\n"
        f"Threshold: {alert.threshold}\n"
        f"Time: {alert.timestamp}\n"
    )

    server = smtplib.SMTP(host, port)
    if user and password:
        server.starttls()
        server.login(user, password)
    server.send_message(msg)
    server.quit()


def _send_log(alert: RuleAlert) -> None:
    """Log alert (always available, no config needed)."""
    log.warning("[%s] %s: %s (field=%s, value=%s, threshold=%s)",
                alert.severity.upper(), alert.rule_name, alert.message,
                alert.field, alert.actual_value, alert.threshold)
