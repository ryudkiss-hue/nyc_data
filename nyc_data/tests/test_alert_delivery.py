"""Tests for alert delivery glue module."""
from unittest.mock import patch, MagicMock

from socrata_toolkit.alert_delivery import deliver_alerts, _detect_channels
from socrata_toolkit.notification_rules import RuleAlert


def _sample_alert():
    return RuleAlert(
        rule_name="test_rule", message="Test alert fired",
        severity="warning", field="pending", actual_value=150,
        threshold=100, timestamp="2025-01-01T00:00:00",
    )


def test_deliver_alerts_log_channel():
    alerts = [_sample_alert()]
    results = deliver_alerts(alerts, channels=["log"])
    assert results["log"] == 1


def test_deliver_alerts_empty():
    results = deliver_alerts([])
    assert results == {}


def test_detect_channels_default():
    channels = _detect_channels()
    assert "log" in channels


@patch.dict("os.environ", {"TEAMS_WEBHOOK_URL": "https://fake.webhook"})
def test_detect_channels_teams():
    channels = _detect_channels()
    assert "teams" in channels


@patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://fake.slack"})
def test_detect_channels_slack():
    channels = _detect_channels()
    assert "slack" in channels


@patch("socrata_toolkit.alert_delivery._requests.post")
@patch.dict("os.environ", {"TEAMS_WEBHOOK_URL": "https://fake.webhook"})
def test_deliver_to_teams(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    results = deliver_alerts([_sample_alert()], channels=["teams"])
    assert results["teams"] == 1
    mock_post.assert_called_once()
    payload = mock_post.call_args[1]["json"]
    assert payload["@type"] == "MessageCard"


@patch("socrata_toolkit.alert_delivery._requests.post")
@patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://fake.slack"})
def test_deliver_to_slack(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    results = deliver_alerts([_sample_alert()], channels=["slack"])
    assert results["slack"] == 1
