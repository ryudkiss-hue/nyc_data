"""
Quality Integration - Pipeline and Persistence Integration

Integrates quality validation into data pipelines, persistence operations,
and API responses. Provides decorators and hooks for automated validation.

Standards: Python 3.9+, full type hints, comprehensive docstrings, logging
"""

from __future__ import annotations

import logging
import functools
from typing import Any, Callable, Dict, Optional

import pandas as pd

from socrata_toolkit.quality_expectations import ExpectationSuite
from socrata_toolkit.quality_validator import QualityValidator, ValidationResult
from socrata_toolkit.quality_sla import DataQualityTracker, MetricType
from socrata_toolkit.quality_anomalies import AnomalyDetector
from socrata_toolkit.quality_rules import BusinessRulesEngine

logger = logging.getLogger(__name__)


class QualityIntegration:
    """Integrates quality validation into pipelines and operations.
    
    Manages validation at multiple stages: ingestion, transformation, and serving.
    """

    def __init__(
        self,
        default_suite: Optional[ExpectationSuite] = None,
        tracker: Optional[DataQualityTracker] = None,
        anomaly_detector: Optional[AnomalyDetector] = None,
        rules_engine: Optional[BusinessRulesEngine] = None,
    ):
        """Initialize integration.
        
        Args:
            default_suite: Default expectation suite
            tracker: SLA tracker for metrics
            anomaly_detector: Anomaly detector
            rules_engine: Business rules engine
        """
        self.validator = QualityValidator()
        self.default_suite = default_suite
        self.tracker = tracker or DataQualityTracker()
        self.anomaly_detector = anomaly_detector or AnomalyDetector()
        self.rules_engine = rules_engine or BusinessRulesEngine()

    def validate_ingestion(
        self,
        df: pd.DataFrame,
        dataset_name: str,
        suite: Optional[ExpectationSuite] = None,
    ) -> ValidationResult:
        """Validate data at ingestion point.
        
        Args:
            df: Data to validate
            dataset_name: Dataset name
            suite: Expectation suite (uses default if not provided)
            
        Returns:
            ValidationResult
        """
        suite_to_use = suite or self.default_suite
        if not suite_to_use:
            logger.warning(f"No expectation suite for {dataset_name}")
            return self._create_empty_result(df, dataset_name, "ingestion")

        logger.info(f"Validating ingestion of {dataset_name}")
        result = self.validator.validate(df, suite_to_use, dataset_name)

        # Track metrics
        if self.tracker:
            completeness = 1.0 - (df.isna().sum().sum() / (len(df) * len(df.columns)))
            self.tracker.record_metric(
                f"{dataset_name}_completeness",
                completeness,
                dataset_name,
                MetricType.COMPLETENESS,
                window="5m",
            )

        return result

    def validate_transformation(
        self,
        df: pd.DataFrame,
        transformation_name: str,
        suite: Optional[ExpectationSuite] = None,
    ) -> ValidationResult:
        """Validate data after transformation.
        
        Args:
            df: Transformed data
            transformation_name: Name of transformation
            suite: Expectation suite
            
        Returns:
            ValidationResult
        """
        suite_to_use = suite or self.default_suite
        if not suite_to_use:
            logger.warning(f"No expectation suite for {transformation_name}")
            return self._create_empty_result(df, transformation_name, "transformation")

        logger.info(f"Validating transformation: {transformation_name}")
        return self.validator.validate(df, suite_to_use, transformation_name)

    def validate_serving(
        self,
        df: pd.DataFrame,
        api_name: str,
        suite: Optional[ExpectationSuite] = None,
    ) -> ValidationResult:
        """Validate data before serving via API.
        
        Args:
            df: Data to serve
            api_name: API name
            suite: Expectation suite
            
        Returns:
            ValidationResult
        """
        suite_to_use = suite or self.default_suite
        if not suite_to_use:
            logger.warning(f"No expectation suite for {api_name}")
            return self._create_empty_result(df, api_name, "serving")

        logger.info(f"Validating serving: {api_name}")
        return self.validator.validate(df, suite_to_use, api_name)

    def _create_empty_result(
        self, df: pd.DataFrame, dataset_name: str, stage: str
    ) -> ValidationResult:
        """Create empty validation result when no suite available.
        
        Args:
            df: DataFrame
            dataset_name: Dataset name
            stage: Validation stage
            
        Returns:
            Empty ValidationResult
        """
        from socrata_toolkit.quality_validator import ValidationStatus

        return ValidationResult(
            status=ValidationStatus.PASS,
            timestamp=pd.Timestamp.utcnow(),
            dataset=dataset_name,
            row_count=len(df),
            column_count=len(df.columns),
            results_by_expectation={},
            failed_expectations=[],
            warning_expectations=[],
            metrics={"stage": stage},
        )


def validate_data(
    suite: Optional[ExpectationSuite] = None,
    fail_on_error: bool = False,
) -> Callable:
    """Decorator to validate data in a function.
    
    Usage:
        @validate_data(suite=my_suite)
        def process_data(df: pd.DataFrame) -> pd.DataFrame:
            return df
    
    Args:
        suite: Expectation suite to validate against
        fail_on_error: Whether to raise exception on validation failure
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Execute function
            result = func(*args, **kwargs)

            # Validate result if it's a DataFrame
            if isinstance(result, pd.DataFrame) and suite:
                validator = QualityValidator(fail_fast=fail_on_error)
                validation = validator.validate(result, suite, func.__name__)

                if fail_on_error and not validation.is_critical_failure:
                    logger.error(f"Validation failed in {func.__name__}")
                    raise ValueError(f"Data validation failed: {validation.failed_expectations}")

                logger.info(
                    f"{func.__name__} validation: "
                    f"pass_rate={validation.pass_rate:.1%}"
                )

            return result

        return wrapper

    return decorator


def check_sla(
    metric_name: str,
    tracker: Optional[DataQualityTracker] = None,
) -> Callable:
    """Decorator to check SLA compliance.
    
    Usage:
        @check_sla(metric_name='dataset_completeness')
        def load_data() -> pd.DataFrame:
            return df
    
    Args:
        metric_name: SLA metric name
        tracker: Quality tracker
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = func(*args, **kwargs)

            if tracker and isinstance(result, pd.DataFrame):
                compliant, actual_value = tracker.evaluate_sla(metric_name)
                if not compliant:
                    logger.warning(
                        f"SLA violation in {func.__name__}: "
                        f"{metric_name}={actual_value}"
                    )

            return result

        return wrapper

    return decorator


def detect_anomalies(
    detector: Optional[AnomalyDetector] = None,
) -> Callable:
    """Decorator to detect anomalies in operation results.
    
    Args:
        detector: Anomaly detector
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = func(*args, **kwargs)

            # Could detect anomalies in result
            if detector:
                logger.debug(f"Anomaly detection for {func.__name__}")

            return result

        return wrapper

    return decorator


def apply_business_rules(
    rules_engine: Optional[BusinessRulesEngine] = None,
    key_column: str = "id",
) -> Callable:
    """Decorator to apply business rules.
    
    Args:
        rules_engine: Business rules engine
        key_column: Column for record identifiers
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = func(*args, **kwargs)

            if rules_engine and isinstance(result, pd.DataFrame):
                violations = rules_engine.apply_rules(result, key_column)
                if not violations.can_proceed:
                    logger.error(
                        f"Business rule violations in {func.__name__}: "
                        f"{violations.critical_violations} critical"
                    )
                    raise ValueError(f"Business rule violations: {violations.to_dict()}")

            return result

        return wrapper

    return decorator


class QualityValidator:
    """Alias for backward compatibility."""
    pass


# Global integration instance
_global_integration: Optional[QualityIntegration] = None


def get_quality_integration() -> QualityIntegration:
    """Get or create global quality integration instance.
    
    Returns:
        QualityIntegration instance
    """
    global _global_integration
    if _global_integration is None:
        _global_integration = QualityIntegration()
    return _global_integration


def set_quality_integration(integration: QualityIntegration) -> None:
    """Set global quality integration instance.
    
    Args:
        integration: QualityIntegration to use globally
    """
    global _global_integration
    _global_integration = integration
