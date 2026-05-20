"""
Great Expectations Integration - Data Quality Expectations Management

This module provides a wrapper around Great Expectations for declarative quality expectations.
Supports loading/saving expectations from files, creating expectations programmatically,
validating data against suites, and generating validation reports.

Integrates with schema registry (W1) for structural validation and material standards (W2)
for domain-specific rules.

Standards: Python 3.9+, full type hints, comprehensive docstrings, logging
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class ExpectationType(Enum):
    """Types of expectations supported."""
    COLUMN_EXISTS = "column_exists"
    COLUMN_VALUES_TO_BE_IN_SET = "column_values_to_be_in_set"
    COLUMN_VALUES_TO_BE_OF_TYPE = "column_values_to_be_of_type"
    COLUMN_VALUES_TO_NOT_BE_NULL = "column_values_to_not_be_null"
    COLUMN_VALUES_TO_BE_NULL = "column_values_to_be_null"
    COLUMN_VALUES_TO_MATCH_REGEX = "column_values_to_match_regex"
    COLUMN_VALUES_TO_BE_BETWEEN = "column_values_to_be_between"
    TABLE_ROW_COUNT_TO_BE_BETWEEN = "table_row_count_to_be_between"
    COLUMN_VALUE_LENGTHS_TO_BE_BETWEEN = "column_value_lengths_to_be_between"
    EXPECT_CUSTOM_DOMAIN_RULE = "expect_custom_domain_rule"


class SeverityLevel(Enum):
    """Severity levels for expectation failures."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    WARNING = "warning"


@dataclass
class Expectation:
    """Represents a single data quality expectation.
    
    Attributes:
        expectation_type: Type of expectation (enum)
        kwargs: Parameters for the expectation (e.g., column name, values)
        meta: Metadata about the expectation (name, description, severity)
    """
    expectation_type: ExpectationType
    kwargs: Dict[str, Any]
    meta: Dict[str, Any] = field(default_factory=dict)
    severity: SeverityLevel = SeverityLevel.HIGH

    def to_dict(self) -> Dict[str, Any]:
        """Convert expectation to dictionary format."""
        return {
            "expectation_type": self.expectation_type.value,
            "kwargs": self.kwargs,
            "meta": self.meta,
            "severity": self.severity.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Expectation:
        """Create expectation from dictionary."""
        return cls(
            expectation_type=ExpectationType(data["expectation_type"]),
            kwargs=data["kwargs"],
            meta=data.get("meta", {}),
            severity=SeverityLevel(data.get("severity", "high")),
        )


@dataclass
class ExpectationResult:
    """Result of validating a single expectation.
    
    Attributes:
        expectation: The expectation that was evaluated
        passed: Whether the expectation passed
        result_data: Details about the validation result
        exception_message: Error message if validation failed
    """
    expectation: Expectation
    passed: bool
    result_data: Dict[str, Any] = field(default_factory=dict)
    exception_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "expectation": self.expectation.to_dict(),
            "passed": self.passed,
            "result_data": self.result_data,
            "exception_message": self.exception_message,
        }


class ExpectationSuite:
    """Manages a suite of data quality expectations.
    
    An expectation suite is a collection of expectations that can be:
    - Loaded from/saved to JSON files
    - Created programmatically
    - Validated against data
    - Versioned and tracked
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        version: str = "1.0.0",
    ):
        """Initialize expectation suite.
        
        Args:
            name: Name of the suite (e.g., 'sidewalk_inspections')
            description: Description of what this suite validates
            version: Version number for tracking changes
        """
        self.name = name
        self.description = description
        self.version = version
        self.expectations: List[Expectation] = []
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def add_expectation(self, expectation: Expectation) -> None:
        """Add an expectation to the suite.
        
        Args:
            expectation: Expectation to add
        """
        self.expectations.append(expectation)
        self.updated_at = datetime.utcnow()
        logger.debug(
            f"Added expectation {expectation.meta.get('name', 'unnamed')} to suite {self.name}"
        )

    def add_column_exists(
        self,
        column: str,
        severity: SeverityLevel = SeverityLevel.CRITICAL,
    ) -> None:
        """Add expectation that a column exists.
        
        Args:
            column: Column name
            severity: Severity if expectation fails
        """
        expectation = Expectation(
            expectation_type=ExpectationType.COLUMN_EXISTS,
            kwargs={"column": column},
            meta={"name": f"column_{column}_exists"},
            severity=severity,
        )
        self.add_expectation(expectation)

    def add_column_type(
        self,
        column: str,
        dtype: str,
        severity: SeverityLevel = SeverityLevel.HIGH,
    ) -> None:
        """Add expectation for column data type.
        
        Args:
            column: Column name
            dtype: Expected pandas dtype (e.g., 'int64', 'object')
            severity: Severity if expectation fails
        """
        expectation = Expectation(
            expectation_type=ExpectationType.COLUMN_VALUES_TO_BE_OF_TYPE,
            kwargs={"column": column, "type_": dtype},
            meta={"name": f"column_{column}_type_{dtype}"},
            severity=severity,
        )
        self.add_expectation(expectation)

    def add_column_not_null(
        self,
        column: str,
        mostly: float = 1.0,
        severity: SeverityLevel = SeverityLevel.HIGH,
    ) -> None:
        """Add expectation that column values are not null.
        
        Args:
            column: Column name
            mostly: Fraction of non-null values allowed (0.0-1.0), default 1.0 (100%)
            severity: Severity if expectation fails
        """
        expectation = Expectation(
            expectation_type=ExpectationType.COLUMN_VALUES_TO_NOT_BE_NULL,
            kwargs={"column": column, "mostly": mostly},
            meta={"name": f"column_{column}_not_null"},
            severity=severity,
        )
        self.add_expectation(expectation)

    def add_column_values_in_set(
        self,
        column: str,
        values: Set[Any],
        severity: SeverityLevel = SeverityLevel.HIGH,
    ) -> None:
        """Add expectation that column values are in a set.
        
        Args:
            column: Column name
            values: Set of allowed values
            severity: Severity if expectation fails
        """
        expectation = Expectation(
            expectation_type=ExpectationType.COLUMN_VALUES_TO_BE_IN_SET,
            kwargs={"column": column, "value_set": list(values)},
            meta={"name": f"column_{column}_in_set"},
            severity=severity,
        )
        self.add_expectation(expectation)

    def add_column_values_match_regex(
        self,
        column: str,
        regex: str,
        severity: SeverityLevel = SeverityLevel.MEDIUM,
    ) -> None:
        """Add expectation that column values match regex pattern.
        
        Args:
            column: Column name
            regex: Regular expression pattern
            severity: Severity if expectation fails
        """
        expectation = Expectation(
            expectation_type=ExpectationType.COLUMN_VALUES_TO_MATCH_REGEX,
            kwargs={"column": column, "regex": regex},
            meta={"name": f"column_{column}_regex"},
            severity=severity,
        )
        self.add_expectation(expectation)

    def add_column_values_between(
        self,
        column: str,
        min_value: float | None = None,
        max_value: float | None = None,
        severity: SeverityLevel = SeverityLevel.HIGH,
    ) -> None:
        """Add expectation that column values are between min and max.
        
        Args:
            column: Column name
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)
            severity: Severity if expectation fails
        """
        expectation = Expectation(
            expectation_type=ExpectationType.COLUMN_VALUES_TO_BE_BETWEEN,
            kwargs={
                "column": column,
                "min_value": min_value,
                "max_value": max_value,
            },
            meta={"name": f"column_{column}_between"},
            severity=severity,
        )
        self.add_expectation(expectation)

    def add_row_count_between(
        self,
        min_value: int,
        max_value: int,
        severity: SeverityLevel = SeverityLevel.HIGH,
    ) -> None:
        """Add expectation that table has row count within range.
        
        Args:
            min_value: Minimum row count
            max_value: Maximum row count
            severity: Severity if expectation fails
        """
        expectation = Expectation(
            expectation_type=ExpectationType.TABLE_ROW_COUNT_TO_BE_BETWEEN,
            kwargs={"min_value": min_value, "max_value": max_value},
            meta={"name": "row_count_between"},
            severity=severity,
        )
        self.add_expectation(expectation)

    def add_column_value_length_between(
        self,
        column: str,
        min_value: int,
        max_value: int,
        severity: SeverityLevel = SeverityLevel.MEDIUM,
    ) -> None:
        """Add expectation that column value lengths are within range.
        
        Args:
            column: Column name
            min_value: Minimum string length
            max_value: Maximum string length
            severity: Severity if expectation fails
        """
        expectation = Expectation(
            expectation_type=ExpectationType.COLUMN_VALUE_LENGTHS_TO_BE_BETWEEN,
            kwargs={"column": column, "min_value": min_value, "max_value": max_value},
            meta={"name": f"column_{column}_length_between"},
            severity=severity,
        )
        self.add_expectation(expectation)

    def add_custom_rule(
        self,
        rule_name: str,
        rule_func: Callable[[pd.DataFrame], bool],
        severity: SeverityLevel = SeverityLevel.HIGH,
    ) -> None:
        """Add custom business rule expectation.
        
        Args:
            rule_name: Name of the rule
            rule_func: Callable that takes DataFrame and returns bool
            severity: Severity if expectation fails
        """
        expectation = Expectation(
            expectation_type=ExpectationType.EXPECT_CUSTOM_DOMAIN_RULE,
            kwargs={"rule_name": rule_name, "rule_func": rule_func},
            meta={"name": f"custom_rule_{rule_name}"},
            severity=severity,
        )
        self.add_expectation(expectation)

    def to_dict(self) -> Dict[str, Any]:
        """Convert suite to dictionary format.
        
        Returns:
            Dictionary representation of the suite
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expectations": [e.to_dict() for e in self.expectations],
        }

    def to_json(self, path: Path | str) -> None:
        """Save suite to JSON file.
        
        Args:
            path: File path to save to
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        logger.info(f"Saved expectation suite {self.name} to {path}")

    @classmethod
    def from_json(cls, path: Path | str) -> ExpectationSuite:
        """Load suite from JSON file.
        
        Args:
            path: File path to load from
            
        Returns:
            Loaded ExpectationSuite
        """
        path = Path(path)
        with open(path) as f:
            data = json.load(f)

        suite = cls(
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
        )

        for exp_data in data.get("expectations", []):
            expectation = Expectation.from_dict(exp_data)
            suite.add_expectation(expectation)

        logger.info(f"Loaded expectation suite {suite.name} from {path}")
        return suite

    def validate(self, df: pd.DataFrame) -> ValidationSuiteResult:
        """Validate a DataFrame against all expectations in the suite.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            ValidationSuiteResult with results for all expectations
        """
        results: List[ExpectationResult] = []

        for expectation in self.expectations:
            result = self._validate_expectation(df, expectation)
            results.append(result)

        return ValidationSuiteResult(
            suite_name=self.name,
            timestamp=datetime.utcnow(),
            total_expectations=len(self.expectations),
            results=results,
        )

    def _validate_expectation(
        self, df: pd.DataFrame, expectation: Expectation
    ) -> ExpectationResult:
        """Validate a single expectation against data.
        
        Args:
            df: DataFrame to validate
            expectation: Expectation to validate
            
        Returns:
            ExpectationResult
        """
        try:
            if expectation.expectation_type == ExpectationType.COLUMN_EXISTS:
                passed = expectation.kwargs["column"] in df.columns
                result_data = {"column_present": passed}

            elif expectation.expectation_type == ExpectationType.COLUMN_VALUES_TO_BE_OF_TYPE:
                column = expectation.kwargs["column"]
                dtype = expectation.kwargs["type_"]
                passed = str(df[column].dtype) == dtype
                result_data = {"actual_dtype": str(df[column].dtype)}

            elif expectation.expectation_type == ExpectationType.COLUMN_VALUES_TO_NOT_BE_NULL:
                column = expectation.kwargs["column"]
                mostly = expectation.kwargs.get("mostly", 1.0)
                non_null_ratio = (df[column].notna().sum()) / len(df)
                passed = non_null_ratio >= mostly
                result_data = {
                    "non_null_ratio": non_null_ratio,
                    "null_count": df[column].isna().sum(),
                }

            elif expectation.expectation_type == ExpectationType.COLUMN_VALUES_TO_BE_IN_SET:
                column = expectation.kwargs["column"]
                value_set = set(expectation.kwargs["value_set"])
                invalid_values = df[~df[column].isin(value_set)]
                passed = len(invalid_values) == 0
                result_data = {
                    "invalid_count": len(invalid_values),
                    "expected_values": list(value_set),
                }

            elif expectation.expectation_type == ExpectationType.COLUMN_VALUES_TO_MATCH_REGEX:
                column = expectation.kwargs["column"]
                regex = expectation.kwargs["regex"]
                matches = df[column].astype(str).str.match(regex)
                passed = matches.all()
                result_data = {
                    "invalid_count": (~matches).sum(),
                    "regex": regex,
                }

            elif expectation.expectation_type == ExpectationType.COLUMN_VALUES_TO_BE_BETWEEN:
                column = expectation.kwargs["column"]
                min_val = expectation.kwargs.get("min_value")
                max_val = expectation.kwargs.get("max_value")
                col_data = pd.to_numeric(df[column], errors="coerce")
                if min_val is not None and max_val is not None:
                    passed = (col_data >= min_val).all() and (col_data <= max_val).all()
                    result_data = {
                        "min": col_data.min(),
                        "max": col_data.max(),
                        "expected_min": min_val,
                        "expected_max": max_val,
                    }
                else:
                    passed = True
                    result_data = {"min": col_data.min(), "max": col_data.max()}

            elif expectation.expectation_type == ExpectationType.TABLE_ROW_COUNT_TO_BE_BETWEEN:
                min_val = expectation.kwargs["min_value"]
                max_val = expectation.kwargs["max_value"]
                row_count = len(df)
                passed = min_val <= row_count <= max_val
                result_data = {
                    "actual_row_count": row_count,
                    "expected_min": min_val,
                    "expected_max": max_val,
                }

            elif expectation.expectation_type == ExpectationType.COLUMN_VALUE_LENGTHS_TO_BE_BETWEEN:
                column = expectation.kwargs["column"]
                min_val = expectation.kwargs["min_value"]
                max_val = expectation.kwargs["max_value"]
                lengths = df[column].astype(str).str.len()
                passed = (lengths >= min_val).all() and (lengths <= max_val).all()
                result_data = {
                    "min_length": lengths.min(),
                    "max_length": lengths.max(),
                    "expected_min": min_val,
                    "expected_max": max_val,
                }

            elif expectation.expectation_type == ExpectationType.EXPECT_CUSTOM_DOMAIN_RULE:
                rule_func = expectation.kwargs["rule_func"]
                passed = rule_func(df)
                result_data = {"custom_rule": expectation.kwargs["rule_name"]}

            else:
                passed = False
                result_data = {"error": "Unknown expectation type"}

            return ExpectationResult(
                expectation=expectation,
                passed=passed,
                result_data=result_data,
            )

        except Exception as e:
            logger.error(f"Error validating expectation: {e}", exc_info=True)
            return ExpectationResult(
                expectation=expectation,
                passed=False,
                exception_message=str(e),
            )


@dataclass
class ValidationSuiteResult:
    """Result of validating an entire expectation suite.
    
    Attributes:
        suite_name: Name of the suite that was validated
        timestamp: When the validation occurred
        total_expectations: Total number of expectations
        results: List of individual expectation results
    """
    suite_name: str
    timestamp: datetime
    total_expectations: int
    results: List[ExpectationResult]

    @property
    def passed_count(self) -> int:
        """Number of expectations that passed."""
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self) -> int:
        """Number of expectations that failed."""
        return sum(1 for r in self.results if not r.passed)

    @property
    def pass_rate(self) -> float:
        """Percentage of expectations that passed (0.0-1.0)."""
        if self.total_expectations == 0:
            return 1.0
        return self.passed_count / self.total_expectations

    @property
    def overall_status(self) -> str:
        """Overall validation status: PASS, WARN, or FAIL."""
        if self.failed_count == 0:
            return "PASS"
        critical_failures = sum(
            1 for r in self.results
            if not r.passed and r.expectation.severity == SeverityLevel.CRITICAL
        )
        return "FAIL" if critical_failures > 0 else "WARN"

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "suite_name": self.suite_name,
            "timestamp": self.timestamp.isoformat(),
            "total_expectations": self.total_expectations,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "pass_rate": self.pass_rate,
            "overall_status": self.overall_status,
            "results": [r.to_dict() for r in self.results],
        }

    def to_json(self, path: Path | str) -> None:
        """Save validation result to JSON file.
        
        Args:
            path: File path to save to
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        logger.info(f"Saved validation result to {path}")


def create_sidewalk_inspections_suite() -> ExpectationSuite:
    """Create expectation suite for sidewalk inspection data.
    
    Returns:
        ExpectationSuite with relevant expectations
    """
    suite = ExpectationSuite(
        name="sidewalk_inspections",
        description="Quality expectations for sidewalk inspection dataset",
        version="1.0.0",
    )

    # Structural expectations
    suite.add_column_exists("inspection_id", SeverityLevel.CRITICAL)
    suite.add_column_exists("location_address", SeverityLevel.CRITICAL)
    suite.add_column_exists("material_type", SeverityLevel.CRITICAL)
    suite.add_column_exists("condition_rating", SeverityLevel.CRITICAL)
    suite.add_column_exists("inspection_date", SeverityLevel.CRITICAL)

    # Type expectations
    suite.add_column_type("inspection_id", "object", SeverityLevel.HIGH)
    suite.add_column_type("condition_rating", "object", SeverityLevel.HIGH)

    # Completeness expectations
    suite.add_column_not_null("inspection_id", mostly=0.99, severity=SeverityLevel.HIGH)
    suite.add_column_not_null("location_address", mostly=0.95, severity=SeverityLevel.HIGH)
    suite.add_column_not_null("material_type", mostly=0.98, severity=SeverityLevel.HIGH)

    # Domain value expectations
    condition_values = {"EXCELLENT", "GOOD", "FAIR", "POOR", "CRITICAL"}
    suite.add_column_values_in_set("condition_rating", condition_values, SeverityLevel.HIGH)

    material_values = {
        "asphalt",
        "concrete",
        "permeable",
        "specialty",
        "metal",
        "brick_stone",
        "composite",
        "other",
    }
    suite.add_column_values_in_set("material_type", material_values, SeverityLevel.HIGH)

    # Row count expectations
    suite.add_row_count_between(100, 1000000, SeverityLevel.MEDIUM)

    return suite


def create_311_complaints_suite() -> ExpectationSuite:
    """Create expectation suite for 311 complaints data.
    
    Returns:
        ExpectationSuite with relevant expectations
    """
    suite = ExpectationSuite(
        name="311_complaints",
        description="Quality expectations for NYC 311 complaints dataset",
        version="1.0.0",
    )

    # Structural expectations
    suite.add_column_exists("complaint_id", SeverityLevel.CRITICAL)
    suite.add_column_exists("complaint_type", SeverityLevel.CRITICAL)
    suite.add_column_exists("latitude", SeverityLevel.CRITICAL)
    suite.add_column_exists("longitude", SeverityLevel.CRITICAL)
    suite.add_column_exists("created_date", SeverityLevel.CRITICAL)

    # Completeness
    suite.add_column_not_null("complaint_id", mostly=0.99, severity=SeverityLevel.HIGH)
    suite.add_column_not_null("complaint_type", mostly=0.95, severity=SeverityLevel.HIGH)
    suite.add_column_not_null("latitude", mostly=0.98, severity=SeverityLevel.HIGH)
    suite.add_column_not_null("longitude", mostly=0.98, severity=SeverityLevel.HIGH)

    # Geographic bounds for NYC (rough)
    suite.add_column_values_between("latitude", 40.5, 40.95, SeverityLevel.HIGH)
    suite.add_column_values_between("longitude", -74.3, -73.7, SeverityLevel.HIGH)

    return suite
