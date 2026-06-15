"""Reproducibility — parameter hashing and run-key generation for auditable analysis."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class ReproducibilityKey:
    """Attach this to every report/export so the exact run can be reconstructed."""

    run_key: str
    param_hash: str
    dataset_hash: str
    analysis_type: str
    created_at: datetime
    params_snapshot: dict[str, Any]

    def to_footer(self) -> str:
        """Return a one-line footer for inclusion in reports/exports."""
        return (
            f"Run: {self.run_key} | "
            f"Analysis: {self.analysis_type} | "
            f"Params: {self.param_hash} | "
            f"Data: {self.dataset_hash} | "
            f"Generated: {self.created_at.strftime('%Y-%m-%d %H:%M UTC')}"
        )


def _sha(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def make_run_key(
    analysis_type: str,
    dataset_key: str,
    row_count: int,
    fetch_timestamp: datetime,
    params: dict | None = None,
) -> ReproducibilityKey:
    """
    Create a reproducibility key that uniquely identifies this exact analysis run.

    Two runs are identical if and only if their run_key matches.
    """
    p = params or {}
    param_str = json.dumps(p, sort_keys=True, default=str)
    param_hash = _sha(param_str)[:16]

    dataset_str = f"{dataset_key}:{row_count}:{fetch_timestamp.isoformat()}"
    dataset_hash = _sha(dataset_str)[:16]

    run_str = f"{analysis_type}:{param_hash}:{dataset_hash}"
    run_key = _sha(run_str)[:12]

    return ReproducibilityKey(
        run_key=run_key,
        param_hash=param_hash,
        dataset_hash=dataset_hash,
        analysis_type=analysis_type,
        created_at=datetime.now(timezone.utc),
        params_snapshot=dict(p),
    )
