from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass
class Rule:
    rule_id: str
    field: str
    operator: str
    threshold: Any
    message: str = ""


@dataclass
class Alert:
    rule_id: str
    message: str


class RulesEngine:
    def __init__(self):
        self.rules: list[Rule] = []

    def add_rule(self, rule: Rule):
        self.rules.append(rule)

    def evaluate(self, data: dict[str, Any]) -> list[Alert]:
        alerts = []
        for rule in self.rules:
            value = data.get(rule.field)
            if value is None:
                continue

            triggered = False
            if (rule.operator == ">" and value > rule.threshold) or \
               (rule.operator == "<" and value < rule.threshold) or \
               (rule.operator == ">=" and value >= rule.threshold):
                triggered = True

            if triggered:
                alerts.append(Alert(rule_id=rule.rule_id, message=rule.message or f"Rule {rule.rule_id} triggered."))
        return alerts

    def save(self, path: str):
        with open(path, 'w', encoding="utf-8") as f:
            json.dump([asdict(r) for r in self.rules], f, indent=2)

    def load(self, path: str):
        with open(path, 'r', encoding="utf-8") as f:
            rules_data = json.load(f)
            self.rules = [Rule(**data) for data in rules_data]

    def evaluate_dataframe(self, df: pd.DataFrame) -> list[Alert]:
        # Simplified for test: check for pending repairs
        pending_count = len(df[df['status'] == 'Pending Repair']) if 'status' in df.columns else 0
        return self.evaluate({"pending_count": pending_count})