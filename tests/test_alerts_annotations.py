"""Tests for threshold alerting and annotation logic (Streamlit-free paths)."""

from __future__ import annotations

from app.utils import alerts


# ---------------------------------------------------------------------------
# alerts — comparison operators
# ---------------------------------------------------------------------------
def test_evaluate_rule_greater_than_breach():
    rule = alerts.ThresholdRule("null_pct", ">", 20.0, "warn")
    res = alerts.evaluate_rule(rule, 35.0)
    assert res.breached is True
    assert res.severity == "warn"


def test_evaluate_rule_no_breach_is_ok_severity():
    rule = alerts.ThresholdRule("health_score", "<", 60.0, "critical")
    res = alerts.evaluate_rule(rule, 80.0)
    assert res.breached is False
    assert res.severity == "ok"


def test_all_comparators():
    cases = [
        (">", 5, 3, True), (">", 2, 3, False),
        (">=", 3, 3, True), ("<", 2, 3, True),
        ("<=", 3, 3, True), ("==", 3, 3, True),
        ("!=", 4, 3, True), ("!=", 3, 3, False),
    ]
    for op, val, thr, expected in cases:
        rule = alerts.ThresholdRule("m", op, float(thr))  # type: ignore[arg-type]
        assert alerts.evaluate_rule(rule, float(val)).breached is expected


def test_evaluate_all_only_present_metrics():
    rules = [
        alerts.ThresholdRule("null_pct", ">", 10.0),
        alerts.ThresholdRule("missing_metric", ">", 1.0),
    ]
    results = alerts.evaluate_all(rules, {"null_pct": 15.0})
    assert len(results) == 1
    assert results[0].rule.metric == "null_pct"


def test_breach_count():
    rules = [
        alerts.ThresholdRule("a", ">", 1.0),
        alerts.ThresholdRule("b", ">", 100.0),
    ]
    results = alerts.evaluate_all(rules, {"a": 5.0, "b": 5.0})
    assert alerts.breach_count(results) == 1


def test_rule_describe_uses_label():
    rule = alerts.ThresholdRule("null_pct", ">", 20.0, "warn", "Null density %")
    assert rule.describe() == "Null density % > 20"


def test_alert_result_message_format():
    rule = alerts.ThresholdRule("x", ">", 10.0, "warn", "X")
    res = alerts.evaluate_rule(rule, 12.0)
    assert "BREACH" in res.message
    assert "12" in res.message


def test_default_rules_present():
    assert len(alerts.DEFAULT_RULES) >= 4
    metrics = {r.metric for r in alerts.DEFAULT_RULES}
    assert "null_pct" in metrics
    assert "health_score" in metrics
