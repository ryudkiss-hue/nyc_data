"""Data governance utilities.

This module provides tools for:
- Data lineage tracking (recording where data came from and how it was transformed)
- Access audit logging (who accessed what and when)
- Data quality scoring (composite score from completeness, validity, consistency, freshness)
- Schema drift detection (comparing a DataFrame against a baseline schema)
- Retention policy helpers (flagging stale or expired records)

Quality Score Weights (see constants below, documented in CLAUDE.md):
  - Completeness: QUALITY_WEIGHT_COMPLETENESS
  - Validity:     QUALITY_WEIGHT_VALIDITY
  - Consistency:  QUALITY_WEIGHT_CONSISTENCY
  - Freshness:    QUALITY_WEIGHT_FRESHNESS

If these values change, update CLAUDE.md section "🐍 Python API — Core Patterns"
to keep documentation in sync with implementation.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Quality Score Weights (Single Source of Truth)
# ---------------------------------------------------------------------------

QUALITY_WEIGHT_COMPLETENESS = 0.35
QUALITY_WEIGHT_VALIDITY = 0.25
QUALITY_WEIGHT_CONSISTENCY = 0.25
QUALITY_WEIGHT_FRESHNESS = 0.15

_WEIGHT_SUM = (
    QUALITY_WEIGHT_COMPLETENESS
    + QUALITY_WEIGHT_VALIDITY
    + QUALITY_WEIGHT_CONSISTENCY
    + QUALITY_WEIGHT_FRESHNESS
)
assert (
    abs(_WEIGHT_SUM - 1.0) < 0.001
), f"Quality score weights must sum to 1.0, got {_WEIGHT_SUM}"


# ---------------------------------------------------------------------------
# Data Lineage
# ---------------------------------------------------------------------------

@dataclass
class LineageEntry:
    """A single step in a data pipeline's lineage."""
    step_name: str
    timestamp: str
    source: str
    action: str  # "fetch", "transform", "filter", "join", "export"
    row_count_in: int
    row_count_out: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LineageRecord:
    """Full lineage record for a dataset pipeline run."""
    dataset_id: str
    run_id: str
    created_at: str
    steps: list[LineageEntry] = field(default_factory=list)

    def add_step(
        self,
        step_name: str,
        source: str,
        action: str,
        row_count_in: int,
        row_count_out: int,
        **metadata: Any,
    ) -> None:
        self.steps.append(LineageEntry(
            step_name=step_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source=source,
            action=action,
            row_count_in=row_count_in,
            row_count_out=row_count_out,
            metadata=metadata,
        ))

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "steps": [
                {
                    "step_name": s.step_name,
                    "timestamp": s.timestamp,
                    "source": s.source,
                    "action": s.action,
                    "row_count_in": s.row_count_in,
                    "row_count_out": s.row_count_out,
                    "metadata": s.metadata,
                }
                for s in self.steps
            ],
        }

    def save(self, path: str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2, default=str), encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> LineageRecord:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        record = cls(
            dataset_id=data["dataset_id"],
            run_id=data["run_id"],
            created_at=data["created_at"],
        )
        for s in data.get("steps", []):
            record.steps.append(LineageEntry(**s))
        return record


def create_lineage(dataset_id: str, run_id: str | None = None) -> LineageRecord:
    """Create a new lineage record for a pipeline run."""
    if run_id is None:
        run_id = hashlib.sha256(
            f"{dataset_id}-{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:12]
    return LineageRecord(
        dataset_id=dataset_id,
        run_id=run_id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Access Audit Logging
# ---------------------------------------------------------------------------

@dataclass
class AuditEvent:
    """A single audit event."""
    timestamp: str
    actor: str
    action: str  # "read", "write", "delete", "export", "query"
    resource: str
    details: dict[str, Any] = field(default_factory=dict)


class AuditLogger:
    """Append-only audit logger for data access events.

    Events are stored in memory and can be flushed to a JSON file.
    For production use, wire this into a database or log aggregator.
    """

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def log_event(
        self,
        actor: str,
        action: str,
        resource: str,
        **details: Any,
    ) -> AuditEvent:
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor=actor,
            action=action,
            resource=resource,
            details=details,
        )
        self.events.append(event)
        return event

    def query(
        self,
        actor: str | None = None,
        action: str | None = None,
        resource: str | None = None,
    ) -> list[AuditEvent]:
        """Filter audit events by actor, action, or resource."""
        results = self.events
        if actor:
            results = [e for e in results if e.actor == actor]
        if action:
            results = [e for e in results if e.action == action]
        if resource:
            results = [e for e in results if e.resource == resource]
        return results

    def flush(self, path: str) -> int:
        """Write all events to a JSON file and clear the buffer."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        records = [
            {
                "timestamp": e.timestamp,
                "actor": e.actor,
                "action": e.action,
                "resource": e.resource,
                "details": e.details,
            }
            for e in self.events
        ]
        existing = []
        if p.exists():
            try:
                existing = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                existing = []
        existing.extend(records)
        p.write_text(json.dumps(existing, indent=2, default=str), encoding="utf-8")
        count = len(self.events)
        self.events.clear()
        return count


# ---------------------------------------------------------------------------
# Data Quality Scoring
# ---------------------------------------------------------------------------

@dataclass
class QualityScore:
    """Composite data quality score (0-100)."""
    overall: float
    completeness: float  # % non-null cells
    validity: float      # % values passing type/format checks
    consistency: float   # % rows without duplicate keys
    freshness: float     # score based on data recency
    details: dict[str, Any] = field(default_factory=dict)


def compute_quality_score(
    df: pd.DataFrame,
    key_columns: list[str] | None = None,
    date_column: str | None = None,
    freshness_days_threshold: int = 30,
    type_rules: dict[str, str] | None = None,
) -> QualityScore:
    """Compute a composite quality score for a DataFrame.

    Components:
    - Completeness: percentage of non-null cells
    - Validity: percentage of values matching expected types (if type_rules provided)
    - Consistency: percentage of rows that are not duplicate-key violations
    - Freshness: how recent the data is relative to the threshold
    """
    total_cells = df.shape[0] * df.shape[1]
    null_cells = int(df.isnull().sum().sum())
    completeness = (1 - null_cells / max(total_cells, 1)) * 100

    # Validity: check type conformance if rules provided
    if type_rules:
        valid_count = 0
        check_count = 0
        for col, expected in type_rules.items():
            if col not in df.columns:
                continue
            series = df[col].dropna()
            check_count += len(series)
            if expected == "numeric":
                valid_count += pd.to_numeric(series, errors="coerce").notna().sum()
            elif expected == "datetime":
                valid_count += pd.to_datetime(series, errors="coerce").notna().sum()
            elif expected == "string":
                valid_count += series.apply(lambda x: isinstance(x, str)).sum()
            else:
                valid_count += len(series)  # unknown rule: assume valid
        validity = (valid_count / max(check_count, 1)) * 100
    else:
        validity = 100.0

    # Consistency: duplicate key ratio
    if key_columns:
        existing_keys = [c for c in key_columns if c in df.columns]
        if existing_keys:
            dup_count = int(df.duplicated(subset=existing_keys).sum())
            consistency = (1 - dup_count / max(len(df), 1)) * 100
        else:
            consistency = 100.0
    else:
        consistency = 100.0

    # Freshness
    if date_column and date_column in df.columns:
        dates = pd.to_datetime(df[date_column], errors="coerce").dropna()
        if not dates.empty:
            max_date = dates.max()
            if max_date.tzinfo is None:
                max_date = max_date.tz_localize("UTC")
            now = pd.Timestamp.now(tz="UTC")
            age_days = (now - max_date).days
            freshness = max(0.0, (1 - age_days / max(freshness_days_threshold, 1)) * 100)
        else:
            freshness = 0.0
    else:
        freshness = 100.0  # no date column: assume fresh

    # Weighted overall (using module-level weight constants)
    overall = (
        completeness * QUALITY_WEIGHT_COMPLETENESS
        + validity * QUALITY_WEIGHT_VALIDITY
        + consistency * QUALITY_WEIGHT_CONSISTENCY
        + freshness * QUALITY_WEIGHT_FRESHNESS
    )

    return QualityScore(
        overall=round(overall, 2),
        completeness=round(completeness, 2),
        validity=round(validity, 2),
        consistency=round(consistency, 2),
        freshness=round(freshness, 2),
        details={
            "total_cells": total_cells,
            "null_cells": null_cells,
            "key_columns": key_columns or [],
            "date_column": date_column,
        },
    )


# ---------------------------------------------------------------------------
# Schema Drift Detection
# ---------------------------------------------------------------------------

@dataclass
class SchemaDiff:
    """Differences between two schemas."""
    added_columns: list[str]
    removed_columns: list[str]
    type_changes: list[dict[str, str]]
    is_compatible: bool


def detect_schema_drift(
    current_df: pd.DataFrame,
    baseline_schema: dict[str, str],
) -> SchemaDiff:
    """Compare a DataFrame's schema against a baseline schema dict.

    baseline_schema: mapping of column_name -> dtype string (e.g. {"id": "int64", "name": "object"})
    """
    current_schema = {col: str(dtype) for col, dtype in current_df.dtypes.items()}
    baseline_cols = set(baseline_schema.keys())
    current_cols = set(current_schema.keys())

    added = sorted(current_cols - baseline_cols)
    removed = sorted(baseline_cols - current_cols)

    type_changes = []
    for col in baseline_cols & current_cols:
        baseline_type = baseline_schema[col]
        current_type = current_schema[col]
        if baseline_type != current_type:
            type_changes.append({
                "column": col,
                "baseline_type": baseline_type,
                "current_type": current_type,
            })

    # Compatible if no columns were removed and no type changes
    is_compatible = len(removed) == 0 and len(type_changes) == 0

    return SchemaDiff(
        added_columns=added,
        removed_columns=removed,
        type_changes=type_changes,
        is_compatible=is_compatible,
    )


def snapshot_schema(df: pd.DataFrame) -> dict[str, str]:
    """Capture the current schema as a dict suitable for drift detection baselines."""
    return {col: str(dtype) for col, dtype in df.dtypes.items()}


def save_schema_snapshot(df: pd.DataFrame, path: str) -> None:
    """Save a schema snapshot to a JSON file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    schema = snapshot_schema(df)
    p.write_text(json.dumps(schema, indent=2), encoding="utf-8")


def load_schema_snapshot(path: str) -> dict[str, str]:
    """Load a schema snapshot from a JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Retention Policy Helpers
# ---------------------------------------------------------------------------

@dataclass
class RetentionReport:
    """Results from applying a retention policy."""
    total_rows: int
    retained_rows: int
    expired_rows: int
    expired_pct: float
    retention_days: int


def apply_retention_policy(
    df: pd.DataFrame,
    date_column: str,
    retention_days: int = 365,
    reference_date: datetime | None = None,
) -> tuple[pd.DataFrame, RetentionReport]:
    """Flag or filter rows that exceed the retention period.

    Returns a tuple of (retained_df, report).
    Rows older than `retention_days` from `reference_date` (default: now) are excluded.
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc)

    tmp = df.copy()
    dates = pd.to_datetime(tmp[date_column], errors="coerce")

    # Make reference_date tz-aware if dates are tz-naive
    cutoff = pd.Timestamp(reference_date) - pd.Timedelta(days=retention_days)
    if dates.dt.tz is None and cutoff.tzinfo is not None:
        cutoff = cutoff.tz_localize(None)

    mask = dates >= cutoff
    retained = tmp[mask | dates.isna()].copy()  # keep rows with unparseable dates
    expired_count = len(tmp) - len(retained)

    report = RetentionReport(
        total_rows=len(df),
        retained_rows=len(retained),
        expired_rows=expired_count,
        expired_pct=round(expired_count / max(len(df), 1) * 100, 2),
        retention_days=retention_days,
    )
    return retained, report
