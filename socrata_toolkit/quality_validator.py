"""
Quality Validation Engine - Data Quality Validation and Result Aggregation

Validates DataFrames against expectations, handles batch and streaming validation,
and aggregates results. Integrates with the expectation framework for production
data quality checks.

Standards: Python 3.9+, full type hints, comprehensive docstrings, logging
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd

from socrata_toolkit.quality_expectations import (
    ExpectationSuite,
    ValidationSuiteResult,
    ExpectationResult,
    SeverityLevel,
)

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Overall validation status."""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class ValidationResult:
    """Result of validating a DataFrame.
    
    Attributes:
        status: Overall status (PASS, WARN, FAIL)
        timestamp: When validation occurred
        dataset: Name of dataset validated
        row_count: Number of rows processed
        column_count: Number of columns
        results_by_expectation: Details for each expectation
        failed_expectations: List of failed expectations
        warning_expectations: List of warning-level failed expectations
        metrics: Summary metrics
        failed_rows: Sample of rows that failed validation
    """
    status: ValidationStatus
    timestamp: datetime
    dataset: str
    row_count: int
    column_count: int
    results_by_expectation: Dict[str, Any]
    failed_expectations: List[str]
    warning_expectations: List[str]
    metrics: Dict[str, Any]
    failed_rows: Optional[pd.DataFrame] = None

    @property
    def pass_rate(self) -> float:
        """Percentage of expectations that passed."""
        total = len(self.results_by_expectation)
        passed = total - len(self.failed_expectations)
        return passed / total if total > 0 else 1.0

    @property
    def is_critical_failure(self) -> bool:
        """Whether there are critical failures."""
        critical_fails = [
            e for e in self.failed_expectations
            if self.results_by_expectation[e].get("severity") == "critical"
        ]
        return len(critical_fails) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "dataset": self.dataset,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "pass_rate": self.pass_rate,
            "is_critical_failure": self.is_critical_failure,
            "failed_count": len(self.failed_expectations),
            "warning_count": len(self.warning_expectations),
            "metrics": self.metrics,
            "failed_expectations": self.failed_expectations,
            "warning_expectations": self.warning_expectations,
        }


class QualityValidator:
    """Validates data against expectations.
    
    Supports batch validation of entire DataFrames and streaming validation
    of individual records. Produces detailed ValidationResult objects.
    """

    def __init__(self, fail_fast: bool = False):
        """Initialize validator.
        
        Args:
            fail_fast: Stop validation on first critical failure
        """
        self.fail_fast = fail_fast

    def validate(
        self,
        df: pd.DataFrame,
        suite: ExpectationSuite,
        dataset_name: str = "unknown",
    ) -> ValidationResult:
        """Validate a DataFrame against an expectation suite.
        
        Args:
            df: DataFrame to validate
            suite: ExpectationSuite to validate against
            dataset_name: Name of the dataset for reporting
            
        Returns:
            ValidationResult with validation details
        """
        logger.info(
            f"Validating {len(df)} rows against suite {suite.name}"
        )

        # Run validation through expectation suite
        suite_result = suite.validate(df)

        # Build result mapping
        results_by_expectation = {}
        failed_expectations = []
        warning_expectations = []

        for result in suite_result.results:
            exp_name = result.expectation.meta.get("name", "unnamed")
            results_by_expectation[exp_name] = {
                "passed": result.passed,
                "severity": result.expectation.severity.value,
                "result_data": result.result_data,
                "exception_message": result.exception_message,
            }

            if not result.passed:
                if result.expectation.severity == SeverityLevel.CRITICAL:
                    failed_expectations.append(exp_name)
                elif result.expectation.severity in (
                    SeverityLevel.HIGH,
                    SeverityLevel.MEDIUM,
                ):
                    failed_expectations.append(exp_name)
                else:
                    warning_expectations.append(exp_name)

                # Early stopping for critical failures
                if self.fail_fast and result.expectation.severity == SeverityLevel.CRITICAL:
                    logger.warning(f"Critical failure in {exp_name}, stopping validation")
                    break

        # Determine overall status
        if len(failed_expectations) > 0:
            critical_fails = [
                e for e in failed_expectations
                if results_by_expectation[e]["severity"] == "critical"
            ]
            status = ValidationStatus.FAIL if critical_fails else ValidationStatus.WARN
        else:
            status = ValidationStatus.PASS

        # Build metrics
        metrics = {
            "total_expectations": len(suite_result.results),
            "passed_expectations": suite_result.passed_count,
            "failed_expectations": len(failed_expectations),
            "warning_expectations": len(warning_expectations),
            "pass_rate": suite_result.pass_rate,
            "suite_name": suite.name,
            "suite_version": suite.version,
        }

        # Get sample of failed rows (if possible)
        failed_rows = None
        if len(failed_expectations) > 0:
            failed_rows = self._collect_failed_rows(df, suite, failed_expectations)

        validation_result = ValidationResult(
            status=status,
            timestamp=datetime.utcnow(),
            dataset=dataset_name,
            row_count=len(df),
            column_count=len(df.columns),
            results_by_expectation=results_by_expectation,
            failed_expectations=failed_expectations,
            warning_expectations=warning_expectations,
            metrics=metrics,
            failed_rows=failed_rows,
        )

        logger.info(
            f"Validation complete: status={status.value}, "
            f"pass_rate={validation_result.pass_rate:.1%}"
        )

        return validation_result

    def _collect_failed_rows(
        self,
        df: pd.DataFrame,
        suite: ExpectationSuite,
        failed_expectations: List[str],
    ) -> Optional[pd.DataFrame]:
        """Collect sample rows that failed validation.
        
        Args:
            df: DataFrame
            suite: ExpectationSuite
            failed_expectations: List of failed expectation names
            
        Returns:
            Sample DataFrame of failed rows
        """
        try:
            failed_mask = pd.Series([False] * len(df))

            for expectation in suite.expectations:
                exp_name = expectation.meta.get("name", "unnamed")
                if exp_name not in failed_expectations:
                    continue

                # Try to identify which rows failed this expectation
                row_mask = self._get_failing_rows_for_expectation(df, expectation)
                failed_mask = failed_mask | row_mask

            # Return sample of failed rows
            failed_df = df[failed_mask]
            if len(failed_df) > 0:
                return failed_df.head(100)  # Max 100 rows

        except Exception as e:
            logger.debug(f"Could not collect failed rows: {e}")

        return None

    def _get_failing_rows_for_expectation(
        self, df: pd.DataFrame, expectation
    ) -> pd.Series:
        """Identify rows that fail an expectation.
        
        Args:
            df: DataFrame
            expectation: Expectation to check
            
        Returns:
            Boolean Series indicating failing rows
        """
        try:
            from socrata_toolkit.quality_expectations import ExpectationType

            col = expectation.kwargs.get("column")

            if expectation.expectation_type == ExpectationType.COLUMN_VALUES_TO_NOT_BE_NULL:
                return df[col].isna()

            elif expectation.expectation_type == ExpectationType.COLUMN_VALUES_TO_BE_IN_SET:
                value_set = set(expectation.kwargs["value_set"])
                return ~df[col].isin(value_set)

            elif expectation.expectation_type == ExpectationType.COLUMN_VALUES_TO_BE_BETWEEN:
                min_val = expectation.kwargs.get("min_value")
                max_val = expectation.kwargs.get("max_value")
                col_data = pd.to_numeric(df[col], errors="coerce")
                mask = pd.Series([False] * len(df))
                if min_val is not None:
                    mask = mask | (col_data < min_val)
                if max_val is not None:
                    mask = mask | (col_data > max_val)
                return mask

        except Exception as e:
            logger.debug(f"Could not identify failing rows: {e}")

        return pd.Series([False] * len(df))

    def validate_record(
        self,
        record: Dict[str, Any],
        suite: ExpectationSuite,
    ) -> bool:
        """Validate a single record (streaming validation).
        
        Args:
            record: Dictionary with record data
            suite: ExpectationSuite to validate against
            
        Returns:
            True if record passes all critical expectations
        """
        # Convert to single-row DataFrame
        df = pd.DataFrame([record])

        # Check critical expectations only
        for expectation in suite.expectations:
            if expectation.severity != SeverityLevel.CRITICAL:
                continue

            try:
                result = suite._validate_expectation(df, expectation)
                if not result.passed:
                    logger.debug(
                        f"Record failed: {expectation.meta.get('name', 'unnamed')}"
                    )
                    return False
            except Exception as e:
                logger.error(f"Error validating record: {e}")
                return False

        return True


class ValidationResultsAggregator:
    """Aggregates validation results over time.
    
    Tracks validation history, computes statistics, and detects
    patterns in validation performance.
    """

    def __init__(self, max_history: int = 1000):
        """Initialize aggregator.
        
        Args:
            max_history: Maximum number of results to keep
        """
        self.max_history = max_history
        self.results: List[ValidationResult] = []

    def add_result(self, result: ValidationResult) -> None:
        """Add a validation result.
        
        Args:
            result: ValidationResult to add
        """
        self.results.append(result)

        # Keep only recent results
        if len(self.results) > self.max_history:
            self.results = self.results[-self.max_history :]

    def get_statistics(self, dataset: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about validation results.
        
        Args:
            dataset: Filter by dataset name (optional)
            
        Returns:
            Dictionary with statistics
        """
        filtered_results = [
            r for r in self.results
            if dataset is None or r.dataset == dataset
        ]

        if not filtered_results:
            return {}

        # Compute statistics
        pass_count = sum(1 for r in filtered_results if r.status == ValidationStatus.PASS)
        warn_count = sum(1 for r in filtered_results if r.status == ValidationStatus.WARN)
        fail_count = sum(1 for r in filtered_results if r.status == ValidationStatus.FAIL)

        avg_pass_rate = sum(r.pass_rate for r in filtered_results) / len(filtered_results)

        return {
            "total_validations": len(filtered_results),
            "passed": pass_count,
            "warned": warn_count,
            "failed": fail_count,
            "success_rate": pass_count / len(filtered_results) if filtered_results else 0,
            "average_pass_rate": avg_pass_rate,
            "latest_validation": filtered_results[-1].timestamp.isoformat() if filtered_results else None,
        }

    def get_recent_failures(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent validation failures.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of failure details
        """
        failures = [
            r for r in self.results
            if r.status in (ValidationStatus.FAIL, ValidationStatus.WARN)
        ]
        failures = sorted(failures, key=lambda r: r.timestamp, reverse=True)

        return [
            {
                "dataset": r.dataset,
                "timestamp": r.timestamp.isoformat(),
                "status": r.status.value,
                "failed_count": len(r.failed_expectations),
                "failed_expectations": r.failed_expectations,
            }
            for r in failures[:limit]
        ]
