"""
Quality Rules Engine - Business Rules for Data Quality

Implements domain-specific business rules for NYC DOT data quality.
Rules can be HARD (blocking) or SOFT (warning). Integrates with audit trail.

Standards: Python 3.9+, full type hints, comprehensive docstrings, logging
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class RuleSeverity(Enum):
    """Severity of rule violations."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RuleMode(Enum):
    """How rules are enforced."""
    HARD = "hard"  # Block on violation
    SOFT = "soft"  # Warn only


@dataclass
class RuleViolation:
    """A single rule violation.

    Attributes:
        rule_id: Unique rule identifier
        rule_name: Human-readable rule name
        severity: Violation severity
        violation_count: Number of violations
        affected_records: Sample of record keys that violated
        suggested_remediation: How to fix
        timestamp: When violation was detected
    """
    rule_id: str
    rule_name: str
    severity: RuleSeverity
    violation_count: int
    affected_records: list[str] = field(default_factory=list)
    suggested_remediation: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "violation_count": self.violation_count,
            "affected_records": self.affected_records,
            "suggested_remediation": self.suggested_remediation,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RuleViolations:
    """Collection of rule violations.

    Attributes:
        violations: List of violations
        total_violations: Total count
        critical_violations: Count of critical violations
        can_proceed: Whether data passes hard rules
    """
    violations: list[RuleViolation] = field(default_factory=list)

    @property
    def total_violations(self) -> int:
        """Total number of violations."""
        return len(self.violations)

    @property
    def critical_violations(self) -> int:
        """Count of critical violations."""
        return sum(1 for v in self.violations if v.severity == RuleSeverity.CRITICAL)

    @property
    def can_proceed(self) -> bool:
        """Whether data passes all hard rules."""
        return self.critical_violations == 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_violations": self.total_violations,
            "critical_violations": self.critical_violations,
            "can_proceed": self.can_proceed,
            "violations": [v.to_dict() for v in self.violations],
        }


class QualityRule:
    """Base class for quality rules.

    Rules check specific business logic conditions and report violations.
    """

    def __init__(
        self,
        rule_id: str,
        rule_name: str,
        rule_func: Callable[[pd.DataFrame], list[str]],
        severity: RuleSeverity = RuleSeverity.HIGH,
        mode: RuleMode = RuleMode.SOFT,
        remediation: str = "",
    ):
        """Initialize rule.

        Args:
            rule_id: Unique rule identifier
            rule_name: Human-readable name
            rule_func: Function that takes DataFrame, returns list of violating record keys
            severity: Severity level
            mode: HARD or SOFT enforcement
            remediation: Suggested fix
        """
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.rule_func = rule_func
        self.severity = severity
        self.mode = mode
        self.remediation = remediation

    def evaluate(self, df: pd.DataFrame, key_column: str = "id") -> RuleViolation:
        """Evaluate rule against DataFrame.

        Args:
            df: DataFrame to check
            key_column: Column name for record identifiers

        Returns:
            RuleViolation with results
        """
        try:
            violating_keys = self.rule_func(df)
            violation_count = len(violating_keys)

            if violation_count > 0:
                logger.warning(
                    f"Rule {self.rule_id} violated: {violation_count} records"
                )

            return RuleViolation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                severity=self.severity,
                violation_count=violation_count,
                affected_records=violating_keys[:100],  # Limit to 100
                suggested_remediation=self.remediation,
            )

        except Exception as e:
            logger.error(f"Error evaluating rule {self.rule_id}: {e}", exc_info=True)
            return RuleViolation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                severity=RuleSeverity.HIGH,
                violation_count=0,
                suggested_remediation=f"Rule evaluation failed: {str(e)}",
            )


class BusinessRulesEngine:
    """Engine for applying business rules to data.

    Manages rule definitions, evaluation, and violation tracking.
    """

    def __init__(self):
        """Initialize engine."""
        self.rules: dict[str, QualityRule] = {}
        self.evaluation_history: list[dict[str, Any]] = []

    def register_rule(self, rule: QualityRule) -> None:
        """Register a rule.

        Args:
            rule: QualityRule to register
        """
        self.rules[rule.rule_id] = rule
        logger.info(f"Registered rule: {rule.rule_id}")

    def apply_rules(
        self,
        df: pd.DataFrame,
        key_column: str = "id",
        rule_ids: set[str] | None = None,
    ) -> RuleViolations:
        """Apply rules to DataFrame.

        Args:
            df: DataFrame to check
            key_column: Column for record identifiers
            rule_ids: Specific rules to apply (None = all)

        Returns:
            RuleViolations with all violations
        """
        violations = RuleViolations()

        rules_to_apply = [
            r for r_id, r in self.rules.items()
            if rule_ids is None or r_id in rule_ids
        ]

        for rule in rules_to_apply:
            violation = rule.evaluate(df, key_column)
            if violation.violation_count > 0:
                violations.violations.append(violation)

        logger.info(
            f"Rules evaluation complete: {violations.total_violations} total violations"
        )

        return violations

    def apply_hard_rules(self, df: pd.DataFrame, key_column: str = "id") -> RuleViolations:
        """Apply only HARD rules (blocking).

        Args:
            df: DataFrame to check
            key_column: Column for record identifiers

        Returns:
            RuleViolations
        """
        hard_rules = {
            r_id: r for r_id, r in self.rules.items()
            if r.mode == RuleMode.HARD
        }

        violations = RuleViolations()
        for rule in hard_rules.values():
            violation = rule.evaluate(df, key_column)
            if violation.violation_count > 0:
                violations.violations.append(violation)

        return violations

    def get_violations_by_severity(
        self, violations: RuleViolations
    ) -> dict[str, list[RuleViolation]]:
        """Group violations by severity.

        Args:
            violations: RuleViolations

        Returns:
            Dict mapping severity to violations
        """
        by_severity: dict[str, list[RuleViolation]] = {}
        for violation in violations.violations:
            severity = violation.severity.value
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(violation)

        return by_severity


# ============================================================================
# Dataset Expectations & Scorecard
# ============================================================================

DATASET_EXPECTATIONS: dict[str, dict] = {
    "sidewalk_inspections": {
        "required_cols": ["inspection_id", "borough", "status", "open_date"],
        "min_rows": 100,
        "date_cols": ["open_date", "close_date"],
        "status_values": ["Open", "Closed", "In Progress"],
    },
    "work_orders": {
        "required_cols": ["work_order_id", "borough"],
        "min_rows": 10,
        "date_cols": [],
        "status_values": [],
    },
    "violations": {
        "required_cols": ["borough"],
        "min_rows": 10,
        "date_cols": [],
        "status_values": [],
    },
    "complaints_311": {
        "required_cols": ["complaint_type", "borough", "created_date"],
        "min_rows": 50,
        "date_cols": ["created_date", "closed_date"],
        "status_values": ["Open", "Closed", "Assigned", "In Progress"],
    },
    "street_permits": {
        "required_cols": ["jobno", "borough"],
        "min_rows": 10,
        "date_cols": ["startdate", "expirationdate"],
        "status_values": [],
    },
}


def validate_expectations(key: str, df: pd.DataFrame) -> list[dict]:
    """Validate a DataFrame against DATASET_EXPECTATIONS for the given key.

    Args:
        key: Dataset key in DATASET_EXPECTATIONS
        df: DataFrame to validate

    Returns:
        List of violation dicts with keys: rule, message, severity
    """
    if key not in DATASET_EXPECTATIONS:
        return [
            {
                "rule": "unknown_key",
                "message": f"No expectations defined for key '{key}'",
                "severity": "high",
            }
        ]

    spec = DATASET_EXPECTATIONS[key]
    violations: list[dict] = []

    # Check required columns
    missing_cols = [c for c in spec.get("required_cols", []) if c not in df.columns]
    if missing_cols:
        violations.append(
            {
                "rule": "required_cols",
                "message": f"Missing required columns: {missing_cols}",
                "severity": "critical",
            }
        )

    # Check min rows
    min_rows = spec.get("min_rows", 0)
    if len(df) < min_rows:
        violations.append(
            {
                "rule": "min_rows",
                "message": f"Row count {len(df)} is below minimum {min_rows}",
                "severity": "high",
            }
        )

    # Check date columns are parseable
    for date_col in spec.get("date_cols", []):
        if date_col in df.columns:
            parsed = pd.to_datetime(df[date_col], errors="coerce")
            null_pct = float(parsed.isna().mean())
            if null_pct > 0.5:
                violations.append(
                    {
                        "rule": "date_parseable",
                        "message": f"Column '{date_col}' has {null_pct:.0%} unparseable values",
                        "severity": "medium",
                    }
                )

    # Check status values
    status_values = spec.get("status_values", [])
    if status_values and "status" in df.columns:
        non_null_status = df["status"].dropna()
        invalid_statuses = non_null_status[~non_null_status.isin(status_values)]
        if not invalid_statuses.empty:
            bad = invalid_statuses.unique().tolist()[:5]
            violations.append(
                {
                    "rule": "status_values",
                    "message": f"Invalid status values found: {bad}",
                    "severity": "medium",
                }
            )

    return violations


def validate_schema(df: pd.DataFrame, expected_cols: list[str]) -> dict:
    """Compare DataFrame columns against an expected schema.

    Args:
        df: DataFrame to inspect
        expected_cols: List of expected column names

    Returns:
        Dict with keys: missing (list), extra (list), matched (list)
    """
    actual = set(df.columns.tolist())
    expected = set(expected_cols)
    return {
        "missing": sorted(expected - actual),
        "extra": sorted(actual - expected),
        "matched": sorted(actual & expected),
    }


def build_data_dictionary(df: pd.DataFrame) -> pd.DataFrame:
    """Build a data dictionary describing each column in a DataFrame.

    Args:
        df: DataFrame to describe

    Returns:
        DataFrame with columns: field, dtype, null_pct, unique_count, sample_values, notes
    """
    if df.empty:
        return pd.DataFrame(
            columns=["field", "dtype", "null_pct", "unique_count", "sample_values", "notes"]
        )

    rows = []
    for col in df.columns:
        series = df[col]
        null_pct = round(float(series.isna().mean()) * 100, 1)
        unique_count = int(series.nunique())
        non_null = series.dropna()
        sample_values = non_null.head(3).tolist() if not non_null.empty else []

        notes_parts: list[str] = []
        if null_pct > 50:
            notes_parts.append("high nulls")
        if unique_count == 1:
            notes_parts.append("constant")
        if len(df) > 0 and unique_count == len(df):
            notes_parts.append("likely key")
        notes = "; ".join(notes_parts)

        rows.append(
            {
                "field": col,
                "dtype": str(series.dtype),
                "null_pct": null_pct,
                "unique_count": unique_count,
                "sample_values": sample_values,
                "notes": notes,
            }
        )

    return pd.DataFrame(rows)


def quality_scorecard(df: pd.DataFrame) -> dict:
    """Compute a 0-100 quality score with weighted component breakdown.

    Score components:
    - completeness (weight 30): % non-null across all cells
    - uniqueness (weight 20): % unique rows vs total
    - validity (weight 30): % rows passing basic type/range checks
    - timeliness (weight 20): recency score based on max date column

    Args:
        df: DataFrame to score

    Returns:
        Dict with keys: total, completeness, uniqueness, validity, timeliness, issues
    """
    issues: list[str] = []

    if df.empty:
        return {
            "total": 0.0,
            "completeness": 0.0,
            "uniqueness": 0.0,
            "validity": 0.0,
            "timeliness": 0.0,
            "issues": ["DataFrame is empty"],
        }

    # Completeness: % non-null across all cells
    total_cells = df.size
    non_null_cells = int(df.notna().sum().sum())
    completeness = round(non_null_cells / total_cells * 100, 1) if total_cells > 0 else 0.0
    if completeness < 80:
        issues.append(f"Completeness is low ({completeness}%)")

    # Uniqueness: % unique rows vs total
    unique_rows = df.drop_duplicates().shape[0]
    uniqueness = round(unique_rows / len(df) * 100, 1)
    if uniqueness < 90:
        issues.append(f"Duplicate rows detected (uniqueness {uniqueness}%)")

    # Validity: % rows free of inf/nan in numeric columns
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        import numpy as np

        validity_mask = pd.Series([True] * len(df), index=df.index)
        for col in numeric_cols:
            col_series = df[col]
            invalid = col_series.isna() | col_series.isin([float("inf"), float("-inf")])
            validity_mask = validity_mask & (~invalid)
        validity = round(float(validity_mask.sum()) / len(df) * 100, 1)
    else:
        validity = 100.0

    if validity < 95:
        issues.append(f"Validity issues found ({validity}% rows pass checks)")

    # Timeliness: find max date value across date-like columns
    date_cols = [
        c
        for c in df.columns
        if "date" in c.lower() or "time" in c.lower() or "created" in c.lower()
    ]
    timeliness = 100.0
    if date_cols:
        max_dates: list[pd.Timestamp] = []
        for col in date_cols:
            try:
                parsed = pd.to_datetime(df[col], errors="coerce")
                if parsed.notna().any():
                    max_dates.append(parsed.max())
            except (TypeError, ValueError):
                pass

        if max_dates:
            latest = max(max_dates)
            now = pd.Timestamp.now(tz=latest.tzinfo)
            days_old = (now - latest).days
            if days_old <= 7:
                timeliness = 100.0
            elif days_old <= 30:
                timeliness = 80.0
            elif days_old <= 90:
                timeliness = 60.0
            elif days_old <= 365:
                timeliness = 40.0
            else:
                timeliness = 20.0
                issues.append(f"Data is stale (latest date is {days_old} days old)")

    total = round(
        completeness * 0.30
        + uniqueness * 0.20
        + validity * 0.30
        + timeliness * 0.20,
        1,
    )

    return {
        "total": total,
        "completeness": completeness,
        "uniqueness": uniqueness,
        "validity": validity,
        "timeliness": timeliness,
        "issues": issues,
    }


# NYC DOT Domain-Specific Rules

def create_sidewalk_rules() -> BusinessRulesEngine:
    """Create business rules for sidewalk inspection data.

    Returns:
        Configured BusinessRulesEngine
    """
    engine = BusinessRulesEngine()

    # Material validity rule
    valid_materials = {
        "asphalt", "concrete", "permeable", "specialty",
        "metal", "brick_stone", "composite", "other"
    }

    def material_type_valid(df: pd.DataFrame) -> list[str]:
        """Check material types are valid."""
        if "material_type" not in df.columns:
            return []
        invalid = df[~df["material_type"].isin(valid_materials)]
        return invalid.get("inspection_id", invalid.index).astype(str).tolist()

    engine.register_rule(QualityRule(
        rule_id="material_valid",
        rule_name="Material Type is Valid",
        rule_func=material_type_valid,
        severity=RuleSeverity.HIGH,
        mode=RuleMode.SOFT,
        remediation="Update material_type to one of: " + ", ".join(valid_materials),
    ))

    # Condition rating rule
    valid_conditions = {"EXCELLENT", "GOOD", "FAIR", "POOR", "CRITICAL"}

    def condition_valid(df: pd.DataFrame) -> list[str]:
        """Check condition ratings are valid."""
        if "condition_rating" not in df.columns:
            return []
        invalid = df[~df["condition_rating"].isin(valid_conditions)]
        return invalid.get("inspection_id", invalid.index).astype(str).tolist()

    engine.register_rule(QualityRule(
        rule_id="condition_rating_valid",
        rule_name="Condition Rating is Valid",
        rule_func=condition_valid,
        severity=RuleSeverity.HIGH,
        mode=RuleMode.SOFT,
        remediation="Update condition_rating to one of: " + ", ".join(valid_conditions),
    ))

    # Geographic bounds rule
    def location_in_nyc(df: pd.DataFrame) -> list[str]:
        """Check location is within NYC bounds."""
        if "latitude" not in df.columns or "longitude" not in df.columns:
            return []

        lat_valid = (df["latitude"] >= 40.5) & (df["latitude"] <= 40.95)
        lon_valid = (df["longitude"] >= -74.3) & (df["longitude"] <= -73.7)
        invalid = df[~(lat_valid & lon_valid)]
        return invalid.get("inspection_id", invalid.index).astype(str).tolist()

    engine.register_rule(QualityRule(
        rule_id="location_in_nyc",
        rule_name="Location is within NYC bounds",
        rule_func=location_in_nyc,
        severity=RuleSeverity.CRITICAL,
        mode=RuleMode.HARD,
        remediation="Correct latitude (40.5-40.95) and longitude (-74.3 to -73.7)",
    ))

    # Inspection date recency rule
    def inspection_recent(df: pd.DataFrame) -> list[str]:
        """Check inspections are recent (within 1 year)."""
        if "inspection_date" not in df.columns:
            return []

        df_copy = df.copy()
        df_copy["inspection_date"] = pd.to_datetime(
            df_copy["inspection_date"], errors="coerce"
        )
        cutoff = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=365)
        invalid = df_copy[df_copy["inspection_date"] < cutoff]
        return invalid.get("inspection_id", invalid.index).astype(str).tolist()

    engine.register_rule(QualityRule(
        rule_id="inspection_recent",
        rule_name="Inspection is Recent (within 1 year)",
        rule_func=inspection_recent,
        severity=RuleSeverity.MEDIUM,
        mode=RuleMode.SOFT,
        remediation="Update inspection_date or flag for re-inspection",
    ))

    # Defect count consistency rule
    def defect_count_logical(df: pd.DataFrame) -> list[str]:
        """Check defect counts are consistent with data."""
        if "defect_count" not in df.columns or "defects" not in df.columns:
            return []

        # Simple check: if defects are listed, count should be > 0
        invalid_rows = []
        for idx, row in df.iterrows():
            defects = row.get("defects", [])
            defect_count = row.get("defect_count", 0)
            if isinstance(defects, (list, str)) and len(str(defects)) > 0 and defect_count == 0:
                invalid_rows.append(row.get("inspection_id", idx))

        return [str(r) for r in invalid_rows]

    engine.register_rule(QualityRule(
        rule_id="defect_count_consistent",
        rule_name="Defect Count is Consistent with Defects",
        rule_func=defect_count_logical,
        severity=RuleSeverity.MEDIUM,
        mode=RuleMode.SOFT,
        remediation="Reconcile defect_count with actual defects listed",
    ))

    # No duplicate inspections on same day
    def no_duplicate_same_day(df: pd.DataFrame) -> list[str]:
        """Check for duplicate inspections on same day/location."""
        if "location_address" not in df.columns or "inspection_date" not in df.columns:
            return []

        df_copy = df.copy()
        df_copy["inspection_date"] = pd.to_datetime(
            df_copy["inspection_date"], errors="coerce"
        ).dt.date

        duplicates = df_copy.groupby(["location_address", "inspection_date"]).size()
        duplicate_locs = duplicates[duplicates > 1].index

        invalid = df_copy[
            df_copy.set_index(["location_address", "inspection_date"]).index.isin(duplicate_locs)
        ]
        return invalid.get("inspection_id", invalid.index).astype(str).tolist()

    engine.register_rule(QualityRule(
        rule_id="no_duplicate_same_day",
        rule_name="No Duplicate Inspections Same Day/Location",
        rule_func=no_duplicate_same_day,
        severity=RuleSeverity.HIGH,
        mode=RuleMode.SOFT,
        remediation="Investigate and remove duplicate inspection records",
    ))

    return engine


def create_311_complaints_rules() -> BusinessRulesEngine:
    """Create business rules for 311 complaints data.

    Returns:
        Configured BusinessRulesEngine
    """
    engine = BusinessRulesEngine()

    # Valid complaint types
    def complaint_type_valid(df: pd.DataFrame) -> list[str]:
        """Check complaint types are valid."""
        if "complaint_type" not in df.columns:
            return []

        # Empty check - complaint_type should not be empty
        invalid = df[df["complaint_type"].isna() | (df["complaint_type"] == "")]
        return invalid.get("complaint_id", invalid.index).astype(str).tolist()

    engine.register_rule(QualityRule(
        rule_id="complaint_type_valid",
        rule_name="Complaint Type is Not Empty",
        rule_func=complaint_type_valid,
        severity=RuleSeverity.CRITICAL,
        mode=RuleMode.HARD,
        remediation="Ensure complaint_type is populated",
    ))

    # Valid status values
    valid_statuses = {"OPEN", "IN PROGRESS", "CLOSED", "ESCALATED", "PENDING"}

    def status_valid(df: pd.DataFrame) -> list[str]:
        """Check statuses are valid."""
        if "status" not in df.columns:
            return []
        invalid = df[~df["status"].isin(valid_statuses)]
        return invalid.get("complaint_id", invalid.index).astype(str).tolist()

    engine.register_rule(QualityRule(
        rule_id="status_valid",
        rule_name="Status is Valid",
        rule_func=status_valid,
        severity=RuleSeverity.HIGH,
        mode=RuleMode.SOFT,
        remediation="Update status to one of: " + ", ".join(valid_statuses),
    ))

    return engine
