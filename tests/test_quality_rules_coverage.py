"""Tests for quality.rules module - Business rules engine."""
from __future__ import annotations

import pandas as pd

from socrata_toolkit.quality.rules import (
    DATASET_EXPECTATIONS,
    BusinessRulesEngine,
    QualityRule,
    RuleMode,
    RuleSeverity,
    RuleViolation,
    RuleViolations,
    validate_expectations,
)

class TestRuleSeverityEnum:
    """Tests for RuleSeverity enum."""

    def test_rule_severity_critical(self):
        assert RuleSeverity.CRITICAL.value == "critical"

    def test_rule_severity_high(self):
        assert RuleSeverity.HIGH.value == "high"

    def test_rule_severity_medium(self):
        assert RuleSeverity.MEDIUM.value == "medium"

    def test_rule_severity_low(self):
        assert RuleSeverity.LOW.value == "low"

class TestRuleModeEnum:
    """Tests for RuleMode enum."""

    def test_rule_mode_hard(self):
        assert RuleMode.HARD.value == "hard"

    def test_rule_mode_soft(self):
        assert RuleMode.SOFT.value == "soft"

class TestRuleViolation:
    """Tests for RuleViolation dataclass."""

    def test_rule_violation_creation(self):
        violation = RuleViolation(
            rule_id="rule1",
            rule_name="Test Rule",
            severity=RuleSeverity.HIGH,
            violation_count=5,
            affected_records=["rec1", "rec2"],
            suggested_remediation="Fix the data",
        )
        assert violation.rule_id == "rule1"
        assert violation.rule_name == "Test Rule"
        assert violation.severity == RuleSeverity.HIGH
        assert violation.violation_count == 5

    def test_rule_violation_to_dict(self):
        violation = RuleViolation(
            rule_id="rule1",
            rule_name="Test Rule",
            severity=RuleSeverity.CRITICAL,
            violation_count=10,
        )
        result = violation.to_dict()
        assert result["rule_id"] == "rule1"
        assert result["rule_name"] == "Test Rule"
        assert result["severity"] == "critical"
        assert result["violation_count"] == 10
        assert "timestamp" in result

    def test_rule_violation_with_defaults(self):
        violation = RuleViolation(
            rule_id="rule1",
            rule_name="Test",
            severity=RuleSeverity.LOW,
            violation_count=0,
        )
        assert violation.affected_records == []
        assert violation.suggested_remediation == ""

class TestRuleViolations:
    """Tests for RuleViolations dataclass."""

    def test_rule_violations_empty(self):
        violations = RuleViolations()
        assert violations.total_violations == 0
        assert violations.critical_violations == 0
        assert violations.can_proceed is True

    def test_rule_violations_with_violations(self):
        v1 = RuleViolation("r1", "Rule 1", RuleSeverity.CRITICAL, 2)
        v2 = RuleViolation("r2", "Rule 2", RuleSeverity.HIGH, 3)
        violations = RuleViolations(violations=[v1, v2])

        assert violations.total_violations == 2
        assert violations.critical_violations == 1
        assert violations.can_proceed is False

    def test_rule_violations_to_dict(self):
        v1 = RuleViolation("r1", "Rule 1", RuleSeverity.HIGH, 1)
        violations = RuleViolations(violations=[v1])
        result = violations.to_dict()

        assert result["total_violations"] == 1
        assert result["critical_violations"] == 0
        assert result["can_proceed"] is True
        assert len(result["violations"]) == 1

class TestQualityRule:
    """Tests for QualityRule class."""

    def test_quality_rule_creation(self):
        def rule_func(df):
            return []

        rule = QualityRule(
            rule_id="rule1",
            rule_name="Test Rule",
            rule_func=rule_func,
            severity=RuleSeverity.HIGH,
            mode=RuleMode.SOFT,
            remediation="Fix it",
        )
        assert rule.rule_id == "rule1"
        assert rule.rule_name == "Test Rule"
        assert rule.severity == RuleSeverity.HIGH

    def test_quality_rule_evaluate_no_violations(self):
        def rule_func(df):
            return []

        rule = QualityRule(
            rule_id="rule1",
            rule_name="Test Rule",
            rule_func=rule_func,
            severity=RuleSeverity.HIGH,
        )
        df = pd.DataFrame({"id": [1, 2, 3]})
        violation = rule.evaluate(df)

        assert violation.violation_count == 0
        assert violation.rule_id == "rule1"

    def test_quality_rule_evaluate_with_violations(self):
        def rule_func(df):
            return ["rec1", "rec2", "rec3"]

        rule = QualityRule(
            rule_id="rule1",
            rule_name="Test Rule",
            rule_func=rule_func,
            severity=RuleSeverity.CRITICAL,
            remediation="Remove invalid records",
        )
        df = pd.DataFrame({"id": [1, 2, 3]})
        violation = rule.evaluate(df)

        assert violation.violation_count == 3
        assert violation.affected_records == ["rec1", "rec2", "rec3"]
        assert violation.severity == RuleSeverity.CRITICAL

    def test_quality_rule_evaluate_with_error(self):
        def rule_func(df):
            raise ValueError("Test error")

        rule = QualityRule(
            rule_id="rule1",
            rule_name="Error Rule",
            rule_func=rule_func,
        )
        df = pd.DataFrame({"id": [1, 2, 3]})
        violation = rule.evaluate(df)

        assert violation.violation_count == 0
        assert "Rule evaluation failed" in violation.suggested_remediation
        assert violation.severity == RuleSeverity.HIGH

class TestBusinessRulesEngine:
    """Tests for BusinessRulesEngine class."""

    def test_engine_initialization(self):
        engine = BusinessRulesEngine()
        assert len(engine.rules) == 0
        assert len(engine.evaluation_history) == 0

    def test_register_rule(self):
        engine = BusinessRulesEngine()

        def rule_func(df):
            return []

        rule = QualityRule(
            rule_id="rule1",
            rule_name="Test Rule",
            rule_func=rule_func,
        )
        engine.register_rule(rule)

        assert len(engine.rules) == 1
        assert "rule1" in engine.rules

    def test_apply_rules_all(self):
        engine = BusinessRulesEngine()

        def rule1_func(df):
            return ["rec1"]

        def rule2_func(df):
            return []

        rule1 = QualityRule(
            rule_id="rule1",
            rule_name="Rule 1",
            rule_func=rule1_func,
            severity=RuleSeverity.HIGH,
        )
        rule2 = QualityRule(
            rule_id="rule2",
            rule_name="Rule 2",
            rule_func=rule2_func,
            severity=RuleSeverity.LOW,
        )
        engine.register_rule(rule1)
        engine.register_rule(rule2)

        df = pd.DataFrame({"id": [1, 2, 3]})
        violations = engine.apply_rules(df)

        assert violations.total_violations == 1
        assert violations.violations[0].rule_id == "rule1"

    def test_apply_rules_specific(self):
        engine = BusinessRulesEngine()

        def rule1_func(df):
            return ["rec1"]

        def rule2_func(df):
            return ["rec2"]

        rule1 = QualityRule("rule1", "Rule 1", rule1_func)
        rule2 = QualityRule("rule2", "Rule 2", rule2_func)
        engine.register_rule(rule1)
        engine.register_rule(rule2)

        df = pd.DataFrame({"id": [1, 2]})
        violations = engine.apply_rules(df, rule_ids={"rule1"})

        assert violations.total_violations == 1
        assert violations.violations[0].rule_id == "rule1"

    def test_apply_hard_rules(self):
        engine = BusinessRulesEngine()

        def hard_func(df):
            return ["rec1"]

        def soft_func(df):
            return ["rec2"]

        hard_rule = QualityRule(
            "hard1", "Hard Rule", hard_func, mode=RuleMode.HARD
        )
        soft_rule = QualityRule(
            "soft1", "Soft Rule", soft_func, mode=RuleMode.SOFT
        )
        engine.register_rule(hard_rule)
        engine.register_rule(soft_rule)

        df = pd.DataFrame({"id": [1, 2]})
        violations = engine.apply_hard_rules(df)

        assert violations.total_violations == 1
        assert violations.violations[0].rule_id == "hard1"

    def test_get_violations_by_severity(self):
        engine = BusinessRulesEngine()
        v1 = RuleViolation("r1", "Rule 1", RuleSeverity.CRITICAL, 1)
        v2 = RuleViolation("r2", "Rule 2", RuleSeverity.HIGH, 1)
        v3 = RuleViolation("r3", "Rule 3", RuleSeverity.HIGH, 1)
        violations = RuleViolations(violations=[v1, v2, v3])

        by_severity = engine.get_violations_by_severity(violations)

        assert "critical" in by_severity
        assert "high" in by_severity
        assert len(by_severity["critical"]) == 1
        assert len(by_severity["high"]) == 2

class TestValidateExpectations:
    """Tests for validate_expectations function."""

    def test_validate_expectations_unknown_key(self):
        df = pd.DataFrame({"col": [1, 2, 3]})
        violations = validate_expectations("unknown_dataset", df)

        assert len(violations) == 1
        assert violations[0]["rule"] == "unknown_key"
        assert violations[0]["severity"] == "high"

    def test_validate_expectations_sidewalk_inspections_missing_cols(self):
        df = pd.DataFrame({"id": [1, 2, 3]})
        violations = validate_expectations("sidewalk_inspections", df)

        assert any(v["rule"] == "required_cols" for v in violations)

    def test_validate_expectations_sidewalk_inspections_valid(self):
        df = pd.DataFrame({
            "inspection_id": [1, 2, 3, 4, 5] * 30,  # 150 rows to exceed min_rows
            "borough": ["MN", "BK", "QN", "BX", "SI"] * 30,
            "status": ["Open", "Closed"] * 75,
            "open_date": pd.date_range("2024-01-01", periods=150),
        })
        violations = validate_expectations("sidewalk_inspections", df)

        # Should have no critical violations for valid data
        critical_violations = [v for v in violations if v["severity"] == "critical"]
        assert len(critical_violations) == 0

    def test_validate_expectations_work_orders(self):
        df = pd.DataFrame({
            "work_order_id": range(1, 20),
            "borough": ["MN"] * 19,
        })
        violations = validate_expectations("work_orders", df)

        # Should pass (has required columns and > min_rows)
        critical_violations = [v for v in violations if v["severity"] == "critical"]
        assert len(critical_violations) == 0

    def test_validate_expectations_violations(self):
        df = pd.DataFrame({
            "borough": ["MN", "BK"],
        })
        violations = validate_expectations("violations", df)

        # Should have no critical violations (has required column)
        critical_violations = [v for v in violations if v["severity"] == "critical"]
        assert len(critical_violations) == 0

    def test_validate_expectations_complaints_311_empty(self):
        df = pd.DataFrame({
            "complaint_type": ["type1"],
            "borough": ["MN"],
            "created_date": pd.date_range("2024-01-01", periods=1),
        })
        violations = validate_expectations("complaints_311", df)

        # Should have min_rows violation
        assert any("min" in v.get("message", "").lower() for v in violations)

    def test_dataset_expectations_keys_exist(self):
        """Verify all expected dataset keys are defined."""
        expected_keys = [
            "sidewalk_inspections",
            "work_orders",
            "violations",
            "complaints_311",
            "street_permits",
        ]
        for key in expected_keys:
            assert key in DATASET_EXPECTATIONS
