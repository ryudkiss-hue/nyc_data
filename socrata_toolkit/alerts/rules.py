# socrata_toolkit/alerts/rules.py
from dataclasses import asdict, dataclass, field
import json
from typing import Any
import pandas as pd

@dataclass
class Rule:
    name: str
    field: str
    operator: str
    threshold: Any
    message: str = ""

@dataclass
class Alert:
    rule_name: str
    message: str
    timestamp: str

class RulesEngine:
    def __init__(self):
        self.rules: list[Rule] = []

    def add_rule(self, rule: Rule):
        self.rules.append(rule)

    def evaluate(self, data: dict[str, Any]) -> list[Alert]:
        from datetime import datetime, timezone
        alerts = []
        for rule in self.rules:
            val = data.get(rule.field)
            if val is None:
                continue
            
            triggered = False
            if rule.operator == ">":
                triggered = val > rule.threshold
            elif rule.operator == "<":
                triggered = val < rule.threshold
            elif rule.operator == ">=":
                triggered = val >= rule.threshold
            elif rule.operator == "<=":
                triggered = val <= rule.threshold
            elif rule.operator == "==":
                triggered = val == rule.threshold
            
            if triggered:
                msg = rule.message or f"Rule {rule.name} triggered for {rule.field}"
                alerts.append(Alert(rule.name, msg, datetime.now(timezone.utc).isoformat()))
        return alerts

    def evaluate_dataframe(self, df: pd.DataFrame) -> list[Alert]:
        # Simple implementation: evaluate based on counts or aggregates
        data = {
            "pending_count": len(df[df["status"].str.lower().str.contains("pending", na=False)]) if "status" in df.columns else 0,
            "total_count": len(df)
        }
        return self.evaluate(data)

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump([asdict(r) for r in self.rules], f)

    def load(self, path: str):
        with open(path, "r") as f:
            data = json.load(f)
            self.rules = [Rule(**r) for r in data]
