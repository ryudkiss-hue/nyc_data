"""Notification Rules Engine for DOT Sidewalk Toolkit.

User-configurable rules that evaluate data conditions and trigger
notifications. Rules are persisted as JSON for easy editing.

Example::

    from socrata_toolkit.alerts.rules import RulesEngine, Rule

    engine = RulesEngine()
    engine.add_rule(Rule("manhattan_backlog", field="pending_count", operator=">", threshold=200,
                         borough="MANHATTAN", message="Manhattan backlog exceeds 200"))
    engine.add_rule(Rule("low_cpi", field="cpi", operator="<", threshold=0.9,
                         message="CPI dropped below 0.9"))
    alerts = engine.evaluate(metrics_dict)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Rule:
    """A notification rule."""
    name: str
    field: str
    operator: str  # ">", "<", ">=", "<=", "==", "!="
    threshold: float
    message: str = ""
    severity: str = "warning"  # "info", "warning", "critical"
    borough: str = ""
    category: str = ""
    enabled: bool = True
    cooldown_minutes: int = 60

@dataclass
class RuleAlert:
    """An alert triggered by a rule."""
    rule_name: str
    message: str
    severity: str
    field: str
    actual_value: float
    threshold: float
    timestamp: str

class RulesEngine:
    """Evaluate rules against data and produce alerts."""

    def __init__(self) -> None:
        self.rules: list[Rule] = []
        self.alerts_history: list[RuleAlert] = []

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)

    def evaluate(self, data: dict[str, Any]) -> list[RuleAlert]:
        """Evaluate all rules against a data dict. Returns triggered alerts."""
        alerts = []
        for rule in self.rules:
            if not rule.enabled:
                continue
            value = data.get(rule.field)
            if value is None:
                continue
            try:
                val = float(value)
            except (TypeError, ValueError):
                continue

            triggered = False
            if rule.operator == ">" and val > rule.threshold:
                triggered = True
            elif rule.operator == "<" and val < rule.threshold:
                triggered = True
            elif rule.operator == ">=" and val >= rule.threshold:
                triggered = True
            elif rule.operator == "<=" and val <= rule.threshold:
                triggered = True
            elif rule.operator == "==" and val == rule.threshold:
                triggered = True
            elif rule.operator == "!=" and val != rule.threshold:
                triggered = True

            if triggered:
                msg = rule.message or f"Rule '{rule.name}': {rule.field} is {val} ({rule.operator} {rule.threshold})"
                alert = RuleAlert(
                    rule_name=rule.name, message=msg, severity=rule.severity,
                    field=rule.field, actual_value=val, threshold=rule.threshold,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                alerts.append(alert)
                self.alerts_history.append(alert)

        return alerts

    def evaluate_dataframe(self, df, borough_col: str = "borough", status_col: str = "status") -> list[RuleAlert]:
        """Evaluate rules against aggregated DataFrame metrics."""
        data = {
            "row_count": len(df),
            "pending_count": int((df[status_col] == "Pending Repair").sum()) if status_col in df.columns else 0,
            "complete_count": int((df[status_col] == "Complete").sum()) if status_col in df.columns else 0,
        }
        if borough_col in df.columns:
            for boro, group in df.groupby(borough_col):
                data[f"{boro.lower()}_count"] = len(group)
                data[f"{boro.lower()}_pending"] = int((group[status_col] == "Pending Repair").sum()) if status_col in group.columns else 0
        return self.evaluate(data)

    def save(self, path: str) -> str:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = [{"name": r.name, "field": r.field, "operator": r.operator, "threshold": r.threshold,
                 "message": r.message, "severity": r.severity, "enabled": r.enabled,
                 "cooldown_minutes": r.cooldown_minutes} for r in self.rules]
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return str(p)

    def load(self, path: str) -> None:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.rules = [Rule(**r) for r in data]
