"""Quality expectations module for defining and validating data quality rules."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd

__all__ = [
    "Expectation", "ExpectationType", "SeverityLevel", "ExpectationSuite",
    "ValidationSuiteResult", "create_sidewalk_inspections_suite",
    "create_311_complaints_suite", "QualityExpectation",
    "define_expectation", "validate_against_expectation"
]

class ExpectationType(str, Enum):
    COLUMN_EXISTS = "column_exists"
    COLUMN_NOT_NULL = "column_not_null"
    COLUMN_VALUES_IN_SET = "column_values_in_set"

class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class Expectation:
    expectation_type: ExpectationType
    kwargs: dict[str, Any]
    meta: dict[str, Any] = field(default_factory=dict)
    severity: SeverityLevel = SeverityLevel.MEDIUM

@dataclass
class ValidationSuiteResult:
    overall_status: str
    passed_count: int
    failed_count: int

class ExpectationSuite:
    def __init__(self, name: str, description: str = "", version: str = "1.0.0"):
        self.name = name
        self.description = description
        self.version = version
        self.expectations: list[Expectation] = []

    def add_column_exists(self, column: str, severity: SeverityLevel = SeverityLevel.CRITICAL):
        self.expectations.append(Expectation(
            expectation_type=ExpectationType.COLUMN_EXISTS,
            kwargs={"column": column},
            meta={"name": f"column_exists_{column}"},
            severity=severity
        ))

    def add_column_not_null(self, column: str, severity: SeverityLevel = SeverityLevel.HIGH, mostly: float = 1.0):
        self.expectations.append(Expectation(
            expectation_type=ExpectationType.COLUMN_NOT_NULL,
            kwargs={"column": column, "mostly": mostly},
            meta={"name": f"column_not_null_{column}"},
            severity=severity
        ))

    def add_column_values_in_set(self, column: str, value_set: set, severity: SeverityLevel = SeverityLevel.HIGH):
        self.expectations.append(Expectation(
            expectation_type=ExpectationType.COLUMN_VALUES_IN_SET,
            kwargs={"column": column, "value_set": value_set},
            meta={"name": f"column_values_in_set_{column}"},
            severity=severity
        ))

    def validate(self, df: pd.DataFrame) -> ValidationSuiteResult:
        passed_count = 0
        failed_count = 0

        for exp in self.expectations:
            col = exp.kwargs.get("column")
            if exp.expectation_type == ExpectationType.COLUMN_EXISTS:
                if col in df.columns:
                    passed_count += 1
                else:
                    failed_count += 1
            elif exp.expectation_type == ExpectationType.COLUMN_NOT_NULL:
                mostly = exp.kwargs.get("mostly", 1.0)
                if col in df.columns:
                    not_null_count = df[col].notna().sum()
                    total_count = len(df)
                    if total_count == 0 or (not_null_count / total_count) >= mostly:
                        passed_count += 1
                    else:
                        failed_count += 1
                else:
                    failed_count += 1
            elif exp.expectation_type == ExpectationType.COLUMN_VALUES_IN_SET:
                value_set = exp.kwargs.get("value_set", set())
                # Handle cases where column has missing values
                if col in df.columns and df[col].dropna().isin(value_set).all():
                    passed_count += 1
                else:
                    failed_count += 1

        status = "FAIL" if failed_count > 0 else "PASS"
        return ValidationSuiteResult(overall_status=status, passed_count=passed_count, failed_count=failed_count)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "expectations": [
                {
                    "expectation_type": e.expectation_type.value,
                    "kwargs": {k: list(v) if isinstance(v, set) else v for k, v in e.kwargs.items()},
                    "meta": e.meta,
                    "severity": e.severity.value
                }
                for e in self.expectations
            ]
        }

def create_sidewalk_inspections_suite() -> ExpectationSuite:
    suite = ExpectationSuite(name="sidewalk_inspections", description="Sidewalk inspections data quality")
    suite.add_column_exists("inspection_id")
    suite.add_column_not_null("inspection_id")
    suite.add_column_exists("material_type")
    suite.add_column_values_in_set("material_type", {"asphalt", "concrete", "permeable", "gravel"})
    suite.add_column_exists("condition_rating")
    suite.add_column_values_in_set("condition_rating", {"EXCELLENT", "GOOD", "FAIR", "POOR", "CRITICAL"})
    return suite

def create_311_complaints_suite() -> ExpectationSuite:
    suite = ExpectationSuite(name="311_complaints", description="311 complaints data quality")
    suite.add_column_exists("unique_key")
    suite.add_column_not_null("unique_key")
    suite.add_column_exists("complaint_type")
    suite.add_column_not_null("created_date")
    return suite

# Legacy types from original file
@dataclass
class QualityExpectation:
    name: str
    rules: dict[str, Any]
    def validate(self, data: Any) -> bool:
        return True

def define_expectation(name: str, rules: dict[str, Any]) -> QualityExpectation:
    return QualityExpectation(name=name, rules=rules)

def validate_against_expectation(data: Any, expectation: QualityExpectation) -> bool:
    return expectation.validate(data)
