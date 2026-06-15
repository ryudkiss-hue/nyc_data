"""Analysis assumptions logger for auditable, reproducible analytics."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd


@dataclass
class AnalysisAssumptions:
    run_id: str
    analysis_type: str
    dataset_key: str
    fetch_timestamp: datetime
    row_count: int
    filter_params: dict[str, Any]
    statistical_assumptions: dict[str, Any]  # e.g. {"normality": True, "alpha": 0.05}
    parameter_hash: str
    dataset_hash: str  # sha256 of (fourfour, row_count, fetch_timestamp)
    warnings: list[str] = field(default_factory=list)
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "analysis_type": self.analysis_type,
            "dataset_key": self.dataset_key,
            "fetch_timestamp": self.fetch_timestamp.isoformat(),
            "row_count": self.row_count,
            "filter_params": self.filter_params,
            "statistical_assumptions": self.statistical_assumptions,
            "parameter_hash": self.parameter_hash,
            "dataset_hash": self.dataset_hash,
            "warnings": self.warnings,
            "recorded_at": self.recorded_at.isoformat(),
        }


def _hash_params(params: dict) -> str:
    serialized = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


def _hash_dataset(dataset_key: str, row_count: int, fetch_timestamp: datetime) -> str:
    payload = f"{dataset_key}:{row_count}:{fetch_timestamp.isoformat()}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def log_assumptions(
    analysis_type: str,
    dataset_key: str,
    df: pd.DataFrame,
    fetch_timestamp: datetime,
    filter_params: dict | None = None,
    statistical_assumptions: dict | None = None,
) -> AnalysisAssumptions:
    """
    Record the assumptions and provenance for an analysis run.

    Returns an AnalysisAssumptions record that should be attached to any
    report, export, or visualization produced from this analysis.
    """
    import uuid

    params = filter_params or {}
    assumptions = statistical_assumptions or {"alpha": 0.05, "normality_assumed": False}

    param_hash = _hash_params({**params, **assumptions, "analysis_type": analysis_type})
    dataset_hash = _hash_dataset(dataset_key, len(df), fetch_timestamp)

    warnings: list[str] = []
    if len(df) < 30:
        warnings.append(f"Small sample (n={len(df)}) — statistical tests may be unreliable")
    if len(df) == 0:
        warnings.append("Empty dataset — analysis results will be empty")

    return AnalysisAssumptions(
        run_id=str(uuid.uuid4()),
        analysis_type=analysis_type,
        dataset_key=dataset_key,
        fetch_timestamp=fetch_timestamp,
        row_count=len(df),
        filter_params=params,
        statistical_assumptions=assumptions,
        parameter_hash=param_hash,
        dataset_hash=dataset_hash,
        warnings=warnings,
    )
