"""Anomaly detection for KPI values using statistical methods.

Detects unexpected KPI values using:
- Z-score analysis (value vs rolling mean/stdev)
- Dynamic thresholds (adapt to KPI variance)
- Severity classification (none/low/medium/high)
"""

from typing import List, Optional
from dataclasses import dataclass
import logging
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AnomalyResult:
    """Anomaly detection output."""
    kpi_id: str
    observed_value: float
    expected_value: float
    z_score: float
    is_anomaly: bool
    severity: str

    def to_dict(self) -> dict:
        """Serialize for database insertion."""
        return {
            'observed_value': self.observed_value,
            'expected_value': self.expected_value,
            'z_score': self.z_score,
            'is_anomaly': self.is_anomaly,
            'severity': self.severity
        }


class AnomalyDetector:
    """Detects and classifies anomalies in KPI values."""

    def __init__(self, z_threshold: float = 3.0, min_history: int = 12):
        """Initialize anomaly detector.

        Args:
            z_threshold: Z-score threshold for anomaly (default 3.0 = 3-sigma)
            min_history: Minimum historical points for calculation
        """
        self.z_threshold = z_threshold
        self.min_history = min_history

    def detect(self, kpi_id: str, observed: float,
               historical_values: List[float]) -> AnomalyResult:
        """Detect if value is anomalous.

        Args:
            kpi_id: KPI identifier
            observed: Current observed value
            historical_values: Historical values (chronologically ordered, oldest to newest)

        Returns:
            AnomalyResult with z-score and severity classification
        """

        if len(historical_values) < self.min_history:
            logger.debug(f"KPI {kpi_id}: insufficient history for anomaly detection")
            return AnomalyResult(
                kpi_id=kpi_id,
                observed_value=observed,
                expected_value=np.mean(historical_values) if historical_values else observed,
                z_score=0.0,
                is_anomaly=False,
                severity='none'
            )

        series = np.array(historical_values, dtype=float)

        # Calculate rolling statistics
        mean = np.mean(series)
        stdev = np.std(series)

        # Handle zero variance
        if stdev == 0:
            return AnomalyResult(
                kpi_id=kpi_id,
                observed_value=observed,
                expected_value=mean,
                z_score=0.0,
                is_anomaly=False,
                severity='none'
            )

        # Calculate z-score
        z_score = float((observed - mean) / stdev)

        # Classify severity
        is_anomaly = bool(abs(z_score) > self.z_threshold)
        severity = self._classify_severity(z_score)

        logger.debug(f"KPI {kpi_id}: z_score={z_score:.2f}, severity={severity}, anomaly={is_anomaly}")

        return AnomalyResult(
            kpi_id=kpi_id,
            observed_value=observed,
            expected_value=mean,
            z_score=z_score,
            is_anomaly=is_anomaly,
            severity=severity
        )

    @staticmethod
    def _classify_severity(z_score: float) -> str:
        """Classify anomaly severity based on z-score.

        Severity levels:
        - none: |z| <= 2.0
        - low: 2.0 < |z| <= 2.5
        - medium: 2.5 < |z| <= 3.0
        - high: |z| > 3.0
        """
        abs_z = abs(z_score)

        if abs_z <= 2.0:
            return 'none'
        elif abs_z <= 2.5:
            return 'low'
        elif abs_z <= 3.0:
            return 'medium'
        else:
            return 'high'


def create_anomaly_detector(z_threshold: float = 3.0) -> AnomalyDetector:
    """Factory for anomaly detector."""
    return AnomalyDetector(z_threshold=z_threshold)
