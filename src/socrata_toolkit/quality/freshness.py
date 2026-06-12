"""Data freshness monitoring and SLA compliance tracking.

This module provides comprehensive freshness tracking for datasets, monitoring
staleness, SLA compliance, and alerting on data quality issues related to update
frequency and timeliness.

Key Classes:
    - FreshnessTracker: Core freshness monitoring and SLA computation
    - DatasetFreshness: Metadata class for individual datasets
    - FreshnessAlert: Alert abstraction for staleness violations

Usage:
    tracker = FreshnessTracker(db_dsn='postgresql://...')
    tracker.track_ingestion('dataset-123', datetime.now(timezone.utc), expected_frequency_hours=24)
    status = tracker.get_freshness_status('dataset-123')
    sla_pct = tracker.compute_freshness_sla_pct(period_days=30)
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum

try:
    import psycopg
except ImportError:
    psycopg = None  # type: ignore

# Logging setup
logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels for freshness violations."""
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class DatasetFreshness:
    """Metadata and status for a single dataset's freshness.

    Attributes:
        dataset_id: Unique identifier for the dataset
        dataset_name: Human-readable dataset name
        last_updated_utc: ISO 8601 timestamp of last successful ingestion
        expected_update_frequency_hours: Expected update interval in hours
        sla_threshold_hours: Maximum allowed staleness before SLA violation
    """

    dataset_id: str
    dataset_name: str
    last_updated_utc: datetime
    expected_update_frequency_hours: float
    sla_threshold_hours: float

    def is_fresh(self) -> bool:
        """Check if dataset is fresh relative to SLA threshold.

        Returns:
            bool: True if dataset hasn't violated SLA, False otherwise

        Examples:
            >>> df = DatasetFreshness(
            ...     dataset_id='nyc-311',
            ...     dataset_name='NYC 311 Service Requests',
            ...     last_updated_utc=datetime.now(timezone.utc),
            ...     expected_update_frequency_hours=24,
            ...     sla_threshold_hours=48
            ... )
            >>> df.is_fresh()
            True
        """
        age = datetime.now(timezone.utc) - self.last_updated_utc
        return age.total_seconds() / 3600 < self.sla_threshold_hours

    def days_since_update(self) -> float:
        """Calculate days elapsed since last update.

        Returns:
            float: Number of days since last_updated_utc

        Examples:
            >>> df = DatasetFreshness(
            ...     dataset_id='nyc-311',
            ...     dataset_name='NYC 311 Service Requests',
            ...     last_updated_utc=datetime.now(timezone.utc) - timedelta(days=5),
            ...     expected_update_frequency_hours=24,
            ...     sla_threshold_hours=48
            ... )
            >>> df.days_since_update()
            5.0
        """
        age = datetime.now(timezone.utc) - self.last_updated_utc
        return age.total_seconds() / (24 * 3600)

    def sla_violated(self) -> bool:
        """Check if SLA threshold has been violated.

        Returns:
            bool: True if staleness exceeds sla_threshold_hours

        Examples:
            >>> df = DatasetFreshness(
            ...     dataset_id='nyc-311',
            ...     dataset_name='NYC 311 Service Requests',
            ...     last_updated_utc=datetime.now(timezone.utc) - timedelta(hours=72),
            ...     expected_update_frequency_hours=24,
            ...     sla_threshold_hours=48
            ... )
            >>> df.sla_violated()
            True
        """
        return not self.is_fresh()

    def hours_until_sla_violation(self) -> float:
        """Calculate hours remaining before SLA violation.

        Returns:
            float: Hours until SLA threshold is breached. Negative if already violated.

        Examples:
            >>> df = DatasetFreshness(
            ...     dataset_id='nyc-311',
            ...     dataset_name='NYC 311 Service Requests',
            ...     last_updated_utc=datetime.now(timezone.utc) - timedelta(hours=30),
            ...     expected_update_frequency_hours=24,
            ...     sla_threshold_hours=48
            ... )
            >>> df.hours_until_sla_violation()
            18.0
        """
        age_hours = (datetime.now(timezone.utc) - self.last_updated_utc).total_seconds() / 3600
        return self.sla_threshold_hours - age_hours

@dataclass
class FreshnessAlert:
    """Alert for dataset freshness SLA violations.

    Attributes:
        alert_id: Unique alert identifier
        dataset_id: Dataset that triggered alert
        dataset_name: Human-readable dataset name
        alert_time: ISO 8601 timestamp when alert was generated
        stale_hours: Hours since last update
        sla_threshold_hours: SLA threshold that was exceeded
        severity: Alert severity (warning or critical)
    """

    alert_id: str
    dataset_id: str
    dataset_name: str
    alert_time: datetime
    stale_hours: float
    sla_threshold_hours: float
    severity: AlertSeverity

    @staticmethod
    def from_dataset_freshness(df: DatasetFreshness) -> FreshnessAlert:
        """Create alert from DatasetFreshness instance.

        Args:
            df: DatasetFreshness instance

        Returns:
            FreshnessAlert: Freshness alert with computed fields

        Examples:
            >>> df = DatasetFreshness(
            ...     dataset_id='nyc-311',
            ...     dataset_name='NYC 311 Service Requests',
            ...     last_updated_utc=datetime.now(timezone.utc) - timedelta(hours=72),
            ...     expected_update_frequency_hours=24,
            ...     sla_threshold_hours=48
            ... )
            >>> alert = FreshnessAlert.from_dataset_freshness(df)
            >>> alert.severity == AlertSeverity.CRITICAL
            True
        """
        stale_hours = (datetime.now(timezone.utc) - df.last_updated_utc).total_seconds() / 3600
        hours_over = stale_hours - df.sla_threshold_hours

        # Determine severity: critical if >24 hours over SLA, else warning
        severity = AlertSeverity.CRITICAL if hours_over > 24 else AlertSeverity.WARNING

        return FreshnessAlert(
            alert_id=str(uuid.uuid4()),
            dataset_id=df.dataset_id,
            dataset_name=df.dataset_name,
            alert_time=datetime.now(timezone.utc),
            stale_hours=stale_hours,
            sla_threshold_hours=df.sla_threshold_hours,
            severity=severity,
        )

    def to_dict(self) -> dict:
        """Convert alert to dictionary representation.

        Returns:
            dict: Alert as dictionary with ISO 8601 timestamps

        Examples:
            >>> alert = FreshnessAlert(
            ...     alert_id='alert-123',
            ...     dataset_id='nyc-311',
            ...     dataset_name='NYC 311 Service Requests',
            ...     alert_time=datetime.now(timezone.utc),
            ...     stale_hours=72,
            ...     sla_threshold_hours=48,
            ...     severity=AlertSeverity.CRITICAL
            ... )
            >>> alert_dict = alert.to_dict()
            >>> alert_dict['severity'] == 'critical'
            True
        """
        d = asdict(self)
        d["alert_time"] = self.alert_time.isoformat() + "Z"
        d["severity"] = self.severity.value
        return d

    def to_prometheus_metric(self) -> str:
        """Format alert as Prometheus metric.

        Returns:
            str: Prometheus metric line with labels and timestamp

        Examples:
            >>> alert = FreshnessAlert(
            ...     alert_id='alert-123',
            ...     dataset_id='nyc-311',
            ...     dataset_name='NYC 311 Service Requests',
            ...     alert_time=datetime.now(timezone.utc),
            ...     stale_hours=72,
            ...     sla_threshold_hours=48,
            ...     severity=AlertSeverity.CRITICAL
            ... )
            >>> metric = alert.to_prometheus_metric()
            >>> 'dataset_freshness_sla_violations_total' in metric
            True
        """
        timestamp_ms = int(self.alert_time.timestamp() * 1000)
        return (
            f'dataset_freshness_sla_violations_total'
            f'{{dataset_id="{self.dataset_id}",severity="{self.severity.value}"}} '
            f'1 {timestamp_ms}'
        )

    def to_slack_json(self) -> dict:
        """Format alert as Slack webhook JSON payload.

        Returns:
            dict: Slack message payload with alert details

        Examples:
            >>> alert = FreshnessAlert(
            ...     alert_id='alert-123',
            ...     dataset_id='nyc-311',
            ...     dataset_name='NYC 311 Service Requests',
            ...     alert_time=datetime.now(timezone.utc),
            ...     stale_hours=72,
            ...     sla_threshold_hours=48,
            ...     severity=AlertSeverity.CRITICAL
            ... )
            >>> slack_msg = alert.to_slack_json()
            >>> 'blocks' in slack_msg
            True
        """
        color = "#dc3545" if self.severity == AlertSeverity.CRITICAL else "#ffc107"
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 Data Freshness Alert: {self.dataset_name}",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Dataset ID*\n{self.dataset_id}"},
                        {
                            "type": "mrkdwn",
                            "text": f"*Severity*\n{self.severity.value.upper()}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Stale For*\n{self.stale_hours:.1f} hours",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*SLA Threshold*\n{self.sla_threshold_hours:.0f} hours",
                        },
                    ],
                },
                {
                    "type": "divider",
                },
            ]
        }

    def to_pagerduty(self) -> dict:
        """Format alert as PagerDuty event payload.

        Returns:
            dict: PagerDuty event with alert details

        Examples:
            >>> alert = FreshnessAlert(
            ...     alert_id='alert-123',
            ...     dataset_id='nyc-311',
            ...     dataset_name='NYC 311 Service Requests',
            ...     alert_time=datetime.now(timezone.utc),
            ...     stale_hours=72,
            ...     sla_threshold_hours=48,
            ...     severity=AlertSeverity.CRITICAL
            ... )
            >>> pd_event = alert.to_pagerduty()
            >>> pd_event['severity'] in ['critical', 'warning']
            True
        """
        return {
            "routing_key": "ROUTING_KEY_PLACEHOLDER",
            "event_action": "trigger",
            "dedup_key": self.alert_id,
            "payload": {
                "summary": f"Data freshness SLA violation: {self.dataset_name} stale for {self.stale_hours:.1f}h",
                "severity": self.severity.value,
                "source": "socrata_toolkit",
                "custom_details": {
                    "dataset_id": self.dataset_id,
                    "dataset_name": self.dataset_name,
                    "stale_hours": self.stale_hours,
                    "sla_threshold_hours": self.sla_threshold_hours,
                },
            },
        }

class FreshnessTracker:
    """Core freshness tracking and SLA monitoring for datasets.

    Tracks dataset ingestion timestamps, computes freshness status, monitors
    SLA compliance, and generates alerts for staleness violations.

    Attributes:
        db_dsn: PostgreSQL connection string (optional for in-memory mode)
        table_name: PostgreSQL table name for freshness log

    Examples:
        >>> tracker = FreshnessTracker()  # In-memory mode
        >>> tracker.track_ingestion('nyc-311', datetime.now(timezone.utc), 24)
        >>> status = tracker.get_freshness_status('nyc-311')
        >>> print(f"Fresh: {status['is_fresh']}, SLA Violated: {status['sla_violated']}")
    """

    def __init__(self, db_dsn: str | None = None, table_name: str = "data_freshness_log"):
        """Initialize FreshnessTracker.

        Args:
            db_dsn: PostgreSQL connection string. If None, uses in-memory storage.
            table_name: Name of PostgreSQL table for freshness log

        Raises:
            ImportError: If psycopg not installed when db_dsn is provided
        """
        self.db_dsn = db_dsn
        self.table_name = table_name
        self._in_memory_store: dict[str, DatasetFreshness] = {}

        if db_dsn and psycopg is None:
            logger.warning("psycopg not installed; running in in-memory mode")
            self.db_dsn = None

        if self.db_dsn:
            self._init_db()

    def _init_db(self) -> None:
        """Initialize PostgreSQL schema for freshness tracking.

        Creates data_freshness_log table if not exists with proper indexing
        and partitioning setup.
        """
        if not self.db_dsn:
            return

        try:
            with psycopg.connect(self.db_dsn) as conn:
                with conn.cursor() as cur:
                    # Create main freshness log table with date partitioning
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS {self.table_name} (
                            id BIGSERIAL,
                            dataset_id VARCHAR(255) NOT NULL,
                            dataset_name VARCHAR(512),
                            last_updated_utc TIMESTAMP WITH TIME ZONE NOT NULL,
                            expected_update_frequency_hours DOUBLE PRECISION,
                            sla_threshold_hours DOUBLE PRECISION,
                            ingestion_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            sla_violated BOOLEAN,
                            days_stale DOUBLE PRECISION,
                            PRIMARY KEY (id, ingestion_timestamp)
                        ) PARTITION BY RANGE (ingestion_timestamp);
                    """)

                    # Create indexes for fast lookups
                    cur.execute(f"""
                        CREATE INDEX IF NOT EXISTS {self.table_name}_dataset_id_idx
                        ON {self.table_name} (dataset_id);
                    """)

                    cur.execute(f"""
                        CREATE INDEX IF NOT EXISTS {self.table_name}_ingestion_timestamp_idx
                        ON {self.table_name} (ingestion_timestamp DESC);
                    """)

                    conn.commit()
                    logger.info(f"Initialized freshness tracking table: {self.table_name}")
        except Exception as e:
            logger.error(f"Failed to initialize freshness tracking table: {e}")

    def track_ingestion(
        self,
        dataset_id: str,
        last_updated_utc: datetime,
        expected_frequency_hours: float,
        dataset_name: str | None = None,
        sla_threshold_hours: float | None = None,
    ) -> None:
        """Track dataset ingestion and freshness status.

        Records an ingestion event with freshness metadata. If no SLA threshold
        specified, defaults to 2x expected frequency.

        Args:
            dataset_id: Unique dataset identifier
            last_updated_utc: Timestamp of last successful update (ISO 8601, UTC)
            expected_frequency_hours: Expected update interval in hours
            dataset_name: Optional human-readable dataset name
            sla_threshold_hours: Optional SLA threshold in hours. Defaults to 2x frequency.

        Raises:
            ValueError: If timestamps are not UTC or frequencies are invalid

        Examples:
            >>> tracker = FreshnessTracker()
            >>> tracker.track_ingestion(
            ...     dataset_id='nyc-311',
            ...     last_updated_utc=datetime.now(timezone.utc),
            ...     expected_frequency_hours=24,
            ...     dataset_name='NYC 311 Service Requests'
            ... )
            >>> status = tracker.get_freshness_status('nyc-311')
            >>> print(status['is_fresh'])
            True
        """
        if expected_frequency_hours <= 0:
            raise ValueError(f"expected_frequency_hours must be positive, got {expected_frequency_hours}")

        # Default SLA: 2x expected frequency
        sla_threshold = sla_threshold_hours or (expected_frequency_hours * 2)

        # Create dataset freshness record
        df = DatasetFreshness(
            dataset_id=dataset_id,
            dataset_name=dataset_name or dataset_id,
            last_updated_utc=last_updated_utc,
            expected_update_frequency_hours=expected_frequency_hours,
            sla_threshold_hours=sla_threshold,
        )

        # Store in memory
        self._in_memory_store[dataset_id] = df

        # Persist to database if available
        if self.db_dsn:
            self._persist_to_db(df)

        logger.info(
            f"Tracked ingestion for {dataset_id}: "
            f"updated={last_updated_utc.isoformat()}, "
            f"frequency={expected_frequency_hours}h, "
            f"sla={sla_threshold}h"
        )

    def _persist_to_db(self, df: DatasetFreshness) -> None:
        """Persist freshness record to PostgreSQL.

        Args:
            df: DatasetFreshness instance to persist
        """
        if not self.db_dsn:
            return

        try:
            with psycopg.connect(self.db_dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        INSERT INTO {self.table_name}
                        (dataset_id, dataset_name, last_updated_utc,
                         expected_update_frequency_hours, sla_threshold_hours,
                         sla_violated, days_stale)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            df.dataset_id,
                            df.dataset_name,
                            df.last_updated_utc,
                            df.expected_update_frequency_hours,
                            df.sla_threshold_hours,
                            df.sla_violated(),
                            df.days_since_update(),
                        ),
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"Failed to persist freshness record for {df.dataset_id}: {e}")

    def get_freshness_status(self, dataset_id: str) -> dict:
        """Get current freshness status for a dataset.

        Returns comprehensive freshness information including staleness,
        SLA status, and time until violation.

        Args:
            dataset_id: Dataset identifier

        Returns:
            dict with keys:
                - is_fresh: bool
                - sla_violated: bool
                - days_stale: float
                - hours_stale: float
                - sla_hours_allowed: float
                - hours_until_violation: float
                - dataset_name: str
                - last_updated_utc: str (ISO 8601)

        Raises:
            KeyError: If dataset not found

        Examples:
            >>> tracker = FreshnessTracker()
            >>> tracker.track_ingestion('nyc-311', datetime.now(timezone.utc), 24)
            >>> status = tracker.get_freshness_status('nyc-311')
            >>> print(f"Fresh: {status['is_fresh']}")
            Fresh: True
        """
        if dataset_id not in self._in_memory_store:
            raise KeyError(f"Dataset {dataset_id} not found in freshness tracker")

        df = self._in_memory_store[dataset_id]

        hours_stale = (datetime.now(timezone.utc) - df.last_updated_utc).total_seconds() / 3600

        return {
            "dataset_id": dataset_id,
            "dataset_name": df.dataset_name,
            "is_fresh": df.is_fresh(),
            "sla_violated": df.sla_violated(),
            "days_stale": df.days_since_update(),
            "hours_stale": hours_stale,
            "sla_hours_allowed": df.sla_threshold_hours,
            "hours_until_violation": df.hours_until_sla_violation(),
            "last_updated_utc": df.last_updated_utc.isoformat() + "Z",
            "expected_frequency_hours": df.expected_update_frequency_hours,
        }

    def compute_freshness_sla_pct(self, period_days: int = 30) -> dict:
        """Compute SLA compliance percentage over period.

        Calculates the percentage of time all datasets remained fresh
        (not in violation) over the specified period.

        Args:
            period_days: Number of days to look back (default 30)

        Returns:
            dict with keys:
                - compliance_pct: float (0-100)
                - datasets_tracked: int
                - datasets_violated: int
                - period_days: int

        Examples:
            >>> tracker = FreshnessTracker()
            >>> tracker.track_ingestion('nyc-311', datetime.now(timezone.utc), 24)
            >>> sla_report = tracker.compute_freshness_sla_pct(period_days=30)
            >>> print(f"SLA Compliance: {sla_report['compliance_pct']:.1f}%")
            SLA Compliance: 100.0%
        """
        if not self._in_memory_store:
            return {
                "compliance_pct": 100.0,
                "datasets_tracked": 0,
                "datasets_violated": 0,
                "period_days": period_days,
            }

        total = len(self._in_memory_store)
        violated = sum(1 for df in self._in_memory_store.values() if df.sla_violated())
        compliance_pct = ((total - violated) / total * 100) if total > 0 else 100.0

        return {
            "compliance_pct": compliance_pct,
            "datasets_tracked": total,
            "datasets_violated": violated,
            "period_days": period_days,
        }

    def get_stale_datasets(self) -> list[FreshnessAlert]:
        """Get alerts for all datasets violating SLA.

        Returns:
            list of FreshnessAlert instances for SLA-violated datasets

        Examples:
            >>> tracker = FreshnessTracker()
            >>> tracker.track_ingestion(
            ...     'stale-dataset',
            ...     datetime.now(timezone.utc) - timedelta(hours=72),
            ...     24
            ... )
            >>> alerts = tracker.get_stale_datasets()
            >>> len(alerts) > 0
            True
        """
        alerts = []
        for df in self._in_memory_store.values():
            if df.sla_violated():
                alerts.append(FreshnessAlert.from_dataset_freshness(df))
        return alerts

    def export_metrics(self) -> str:
        """Export freshness metrics in Prometheus format.

        Returns:
            str: Prometheus metrics text format

        Examples:
            >>> tracker = FreshnessTracker()
            >>> tracker.track_ingestion('nyc-311', datetime.now(timezone.utc), 24)
            >>> metrics = tracker.export_metrics()
            >>> 'dataset_freshness_sla_compliance_pct' in metrics
            True
        """
        lines = [
            "# HELP dataset_freshness_sla_compliance_pct SLA compliance percentage",
            "# TYPE dataset_freshness_sla_compliance_pct gauge",
        ]

        sla_report = self.compute_freshness_sla_pct()
        lines.append(f'dataset_freshness_sla_compliance_pct {sla_report["compliance_pct"]}')

        lines.extend(
            [
                "# HELP dataset_hours_since_update Hours since last dataset update",
                "# TYPE dataset_hours_since_update gauge",
            ]
        )

        for df in self._in_memory_store.values():
            hours_stale = (datetime.now(timezone.utc) - df.last_updated_utc).total_seconds() / 3600
            lines.append(
                f'dataset_hours_since_update{{dataset_id="{df.dataset_id}"}} {hours_stale:.2f}'
            )

        return "\n".join(lines)
