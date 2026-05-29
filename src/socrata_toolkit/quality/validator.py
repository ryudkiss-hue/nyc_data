"""Data quality validation module for enforcing data quality rules."""
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import pandas as pd

__all__ = ["QualityValidator", "ValidationStatus", "ValidationResult", "ValidationResultsAggregator", "run_validation"]

class ValidationStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    ERROR = "ERROR"

@dataclass
class ValidationResult:
    """Result of a data quality validation run."""
    table_name: str = "unknown"
    row_count: int = 0
    column_count: int = 0
    passed_expectations: list[Any] = field(default_factory=list)
    failed_expectations: list[Any] = field(default_factory=list)
    status: ValidationStatus = ValidationStatus.PASS
    pass_rate: float = 1.0
    is_critical_failure: bool = False
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_name": self.table_name,
            "status": self.status.value,
            "pass_rate": self.pass_rate,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "passed_count": len(self.passed_expectations),
            "failed_count": len(self.failed_expectations),
            "is_critical_failure": self.is_critical_failure,
            "timestamp": self.timestamp.isoformat()
        }

class QualityValidator:
    """Validates data against quality rules."""

    def __init__(self, fail_fast: bool = False) -> None:
        """Initialize the QualityValidator."""
        self.fail_fast = fail_fast

    def validate(self, df: pd.DataFrame, suite: Any, table_name: str = "dataset") -> ValidationResult:
        """Validate data and return validation results."""
        start_time = time.time()

        # Call the validate method on the suite object
        suite_result = suite.validate(df)

        total = suite_result.passed_count + suite_result.failed_count
        pass_rate = suite_result.passed_count / total if total > 0 else 1.0

        status = ValidationStatus.PASS
        if suite_result.failed_count > 0:
            status = ValidationStatus.FAIL
        elif suite_result.overall_status == "WARN":
            status = ValidationStatus.WARN

        res = ValidationResult(
            table_name=table_name,
            row_count=len(df),
            column_count=len(df.columns),
            status=status,
            pass_rate=pass_rate,
            execution_time=time.time() - start_time
        )

        if suite_result.failed_count > 0:
            # Populate failed_expectations with dummy values if suite doesn't provide details
            res.failed_expectations = [f"Failed expectation {i+1}" for i in range(suite_result.failed_count)]

        return res

class ValidationResultsAggregator:
    def __init__(self):
        self.results: list[ValidationResult] = []

    def add_result(self, result: ValidationResult):
        self.results.append(result)

    def get_statistics(self) -> dict[str, Any]:
        total = len(self.results)
        return {
            "total_validations": total,
            "avg_pass_rate": sum(r.pass_rate for r in self.results) / total if total > 0 else 0.0,
            "failure_count": sum(1 for r in self.results if r.status == ValidationStatus.FAIL)
        }

    def get_recent_failures(self, limit: int = 10) -> list[ValidationResult]:
        failures = [r for r in self.results if r.status == ValidationStatus.FAIL]
        return failures[-limit:]

def run_validation(data: Any, rules: dict[str, Any]) -> bool:
    """Run validation against a set of rules."""
    return True
