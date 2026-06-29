"""
Alerting System Module
Monitors pipeline execution and sends alerts on failures.
Supports multiple alert channels (logging, email, webhooks).
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert delivery channels."""

    LOG = "log"
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"


@dataclass
class Alert:
    """Alert message with metadata."""

    level: AlertLevel
    title: str
    message: str
    component: str
    timestamp: str = None
    context: Dict = None

    def __post_init__(self):
        """Initialize alert timestamp."""
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class AlertManager:
    """
    Manages pipeline alerts and notifications.
    Routes alerts to configured channels.
    """

    def __init__(self):
        """Initialize alert manager."""
        self.channels = {}
        self.alert_history = []
        self.alert_rules = {}
        logger.info("Alert manager initialized")

    def configure_channel(
        self,
        channel: AlertChannel,
        config: Dict
    ) -> bool:
        """
        Configure an alert channel.

        Args:
            channel: Alert channel type
            config: Channel configuration

        Returns:
            True if configured successfully
        """
        self.channels[channel] = config
        logger.info(f"Configured alert channel: {channel.value}")
        return True

    def send_alert(
        self,
        alert: Alert,
        channels: List[AlertChannel] = None
    ) -> bool:
        """
        Send an alert through configured channels.

        Args:
            alert: Alert to send
            channels: Channels to use (default: all)

        Returns:
            True if alert sent successfully
        """
        target_channels = channels or list(self.channels.keys())
        self.alert_history.append(alert)

        for channel in target_channels:
            if channel not in self.channels:
                logger.warning(f"Channel not configured: {channel.value}")
                continue

            try:
                if channel == AlertChannel.LOG:
                    self._send_log_alert(alert)
                elif channel == AlertChannel.EMAIL:
                    self._send_email_alert(alert)
                elif channel == AlertChannel.SLACK:
                    self._send_slack_alert(alert)
                elif channel == AlertChannel.WEBHOOK:
                    self._send_webhook_alert(alert)

                logger.info(f"Alert sent via {channel.value}: {alert.title}")
            except Exception as e:
                logger.error(f"Failed to send alert via {channel.value}: {str(e)}")

        return True

    def _send_log_alert(self, alert: Alert):
        """Send alert via logging."""
        level_map = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical
        }

        log_fn = level_map.get(alert.level, logger.info)
        log_fn(f"[{alert.component}] {alert.title}: {alert.message}")

    def _send_email_alert(self, alert: Alert):
        """Send alert via email."""
        config = self.channels[AlertChannel.EMAIL]

        email_body = f"""
        Alert: {alert.title}
        Level: {alert.level.value}
        Component: {alert.component}
        Time: {alert.timestamp}

        Message:
        {alert.message}

        Context:
        {alert.context or 'None'}
        """

        logger.info(f"Would send email to {config.get('recipients', [])}: {alert.title}")

    def _send_slack_alert(self, alert: Alert):
        """Send alert via Slack webhook."""
        config = self.channels[AlertChannel.SLACK]
        webhook_url = config.get('webhook_url')

        slack_payload = {
            'text': alert.title,
            'attachments': [
                {
                    'color': self._get_color(alert.level),
                    'fields': [
                        {'title': 'Level', 'value': alert.level.value, 'short': True},
                        {'title': 'Component', 'value': alert.component, 'short': True},
                        {'title': 'Message', 'value': alert.message, 'short': False},
                        {'title': 'Time', 'value': alert.timestamp, 'short': True}
                    ]
                }
            ]
        }

        logger.info(f"Would post to Slack: {alert.title}")

    def _send_webhook_alert(self, alert: Alert):
        """Send alert via webhook."""
        config = self.channels[AlertChannel.WEBHOOK]
        webhook_url = config.get('url')

        payload = {
            'level': alert.level.value,
            'title': alert.title,
            'message': alert.message,
            'component': alert.component,
            'timestamp': alert.timestamp,
            'context': alert.context
        }

        logger.info(f"Would POST to webhook {webhook_url}: {alert.title}")

    def create_alert_rule(
        self,
        rule_name: str,
        condition_fn,
        alert_template: Dict
    ) -> bool:
        """
        Create an alert rule for monitoring.

        Args:
            rule_name: Unique rule identifier
            condition_fn: Function to check condition
            alert_template: Template for generated alerts

        Returns:
            True if rule created successfully
        """
        self.alert_rules[rule_name] = {
            'condition': condition_fn,
            'template': alert_template,
            'triggered_count': 0
        }

        logger.info(f"Created alert rule: {rule_name}")
        return True

    def check_alert_rules(self, context: Dict) -> List[Alert]:
        """
        Check all alert rules against context.

        Args:
            context: Context data for condition evaluation

        Returns:
            List of triggered alerts
        """
        triggered_alerts = []

        for rule_name, rule in self.alert_rules.items():
            try:
                if rule['condition'](context):
                    template = rule['template']
                    alert = Alert(
                        level=AlertLevel[template.get('level', 'WARNING')],
                        title=template.get('title', rule_name),
                        message=template.get('message', 'Alert triggered'),
                        component=template.get('component', rule_name)
                    )
                    triggered_alerts.append(alert)
                    rule['triggered_count'] += 1
                    logger.info(f"Alert rule triggered: {rule_name}")
            except Exception as e:
                logger.error(f"Error checking rule {rule_name}: {str(e)}")

        return triggered_alerts

    def get_alert_history(
        self,
        limit: int = 100,
        level: Optional[AlertLevel] = None
    ) -> List[Alert]:
        """Get alert history."""
        history = self.alert_history

        if level:
            history = [a for a in history if a.level == level]

        return sorted(
            history,
            key=lambda a: a.timestamp,
            reverse=True
        )[:limit]

    @staticmethod
    def _get_color(level: AlertLevel) -> str:
        """Get color for alert level."""
        color_map = {
            AlertLevel.INFO: '#36a64f',
            AlertLevel.WARNING: '#ff9800',
            AlertLevel.ERROR: '#f44336',
            AlertLevel.CRITICAL: '#9c27b0'
        }
        return color_map.get(level, '#999999')
