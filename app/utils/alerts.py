"""Threshold alerting / anomaly monitoring.

Pure-logic rule evaluation so it's fully testable without Streamlit. A rule
compares a metric value against a threshold using a comparison operator and
yields a severity when breached.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Comparator = Literal[">", ">=", "<", "<=", "==", "!="]

def _compare(value: float, op: Comparator, threshold: float) -> bool:
    return {
        ">": value > threshold,
        ">=": value >= threshold,
        "<": value < threshold,
        "<=": value <= threshold,
        "==": value == threshold,
        "!=": value != threshold,
    }[op]

@dataclass
class ThresholdRule:
    """A single alerting rule over a named metric."""

    metric: str
    op: Comparator
    threshold: float
    severity: str = "warn"  # ok | info | warn | critical
    label: str = ""

    def describe(self) -> str:
        name = self.label or self.metric
        return f"{name} {self.op} {self.threshold:g}"

@dataclass
class AlertResult:
    """Outcome of evaluating a rule against a value."""

    rule: ThresholdRule
    value: float
    breached: bool
    severity: str = field(default="ok")

    @property
    def message(self) -> str:
        status = "BREACH" if self.breached else "OK"
        return f"[{status}] {self.rule.describe()} (actual: {self.value:g})"

def evaluate_rule(rule: ThresholdRule, value: float) -> AlertResult:
    """Evaluate one rule against a single metric value."""
    breached = _compare(value, rule.op, rule.threshold)
    return AlertResult(
        rule=rule,
        value=value,
        breached=breached,
        severity=rule.severity if breached else "ok",
    )

def evaluate_all(
    rules: list[ThresholdRule], metrics: dict[str, float]
) -> list[AlertResult]:
    """Evaluate every rule whose metric is present in `metrics`."""
    results: list[AlertResult] = []
    for rule in rules:
        if rule.metric in metrics:
            results.append(evaluate_rule(rule, float(metrics[rule.metric])))
    return results

def breach_count(results: list[AlertResult]) -> int:
    """Number of breached rules."""
    return sum(1 for r in results if r.breached)

# Sensible defaults for dataset quality monitoring
DEFAULT_RULES: list[ThresholdRule] = [
    ThresholdRule("null_pct", ">", 20.0, "warn", "Null density %"),
    ThresholdRule("null_pct", ">", 50.0, "critical", "Null density %"),
    ThresholdRule("health_score", "<", 60.0, "warn", "Health score"),
    ThresholdRule("days_stale", ">", 30.0, "critical", "Days since update"),
    ThresholdRule("duplicate_pct", ">", 5.0, "warn", "Duplicate row %"),
]
