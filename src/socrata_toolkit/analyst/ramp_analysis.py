"""Full-corpus ramp analysis for NYC SIM corners."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd

from ..core import SocrataClient, SocrataConfig


def fetch_ramp_full_corpus(api_token: str | None = None) -> pd.DataFrame:
    """Fetch all corners from the e7gc-ub6z SIM dataset with pagination.

    Uses SOCRATA_APP_TOKEN to bypass rate limits. Fetches all 50K+ corners
    from e7gc-ub6z in paginated batches (limit=50000, offset increments).

    Args:
        api_token: Optional Socrata app token. If not provided, uses
                   SOCRATA_APP_TOKEN environment variable.

    Returns:
        pd.DataFrame with columns: corner_id, borough, total_complaints,
        resolved_complaints, in_progress_complaints

    Raises:
        requests.RequestException: If API calls fail after retries.
        ValueError: If api_token is not provided and SOCRATA_APP_TOKEN is not set.
    """
    token = api_token if api_token is not None else os.getenv("SOCRATA_APP_TOKEN")
    if not token:
        raise ValueError(
            "No API token provided. Pass api_token or set SOCRATA_APP_TOKEN environment variable."
        )

    config = SocrataConfig(app_token=token, page_size=50000)
    client = SocrataClient(config)

    # Fetch all rows from the SIM dataset
    rows: list[dict[str, Any]] = []
    for batch in client.fetch_json(
        domain="data.cityofnewyork.us",
        fourfour="e7gc-ub6z",
    ):
        rows.extend(batch)

    df = pd.DataFrame(rows)

    # Keep only expected columns if they exist
    expected_columns = {
        "corner_id",
        "borough",
        "total_complaints",
        "resolved_complaints",
        "in_progress_complaints",
    }
    present_cols = [col for col in expected_columns if col in df.columns]
    if present_cols:
        df = df[present_cols]

    return df


def compute_borough_completion_rates(
    df: pd.DataFrame,
    borough_col: str = "borough",
    total_col: str = "total_complaints",
    resolved_col: str = "resolved_complaints",
    confidence_level: float = 0.95,
    effect_size: float | None = None,
) -> dict:
    """Compute ramp completion rates by borough with Wilson score CIs.

    Returns a dict with borough keys mapping to stats dicts, plus:
      - "comparison_table": DataFrame of all boroughs
      - "overall_completion_rate": float
    """
    import math

    if df.empty:
        return {
            "comparison_table": pd.DataFrame(),
            "overall_completion_rate": 0.0,
        }

    if borough_col not in df.columns:
        raise ValueError(f"Borough column '{borough_col}' not found in DataFrame")
    if total_col not in df.columns:
        raise ValueError(f"Column '{total_col}' not found in DataFrame")
    if resolved_col not in df.columns:
        raise ValueError(f"Column '{resolved_col}' not found in DataFrame")

    if confidence_level >= 0.99:
        z = 2.576
    elif confidence_level >= 0.95:
        z = 1.96
    else:
        z = 1.645

    results: dict[str, Any] = {}
    rows = []
    for borough, grp in df.groupby(borough_col):
        sample_size = len(grp)
        total_count = int(pd.to_numeric(grp[total_col], errors="coerce").fillna(0).sum())
        resolved_count = int(pd.to_numeric(grp[resolved_col], errors="coerce").fillna(0).sum())

        n = total_count
        k = resolved_count

        if n == 0:
            rate, ci_lower, ci_upper = 0.0, 0.0, 0.0
        else:
            rate = k / n
            # Wilson score interval
            denom = 1 + z * z / n
            centre = (rate + z * z / (2 * n)) / denom
            half = (z / denom) * math.sqrt(rate * (1 - rate) / n + z * z / (4 * n * n))
            ci_lower = max(0.0, centre - half)
            ci_upper = min(1.0, centre + half)

        has_power: bool | None = None
        if effect_size is not None:
            if effect_size == 0.0:
                min_sample = 30
            else:
                min_sample = max(10, int(61.4336 / (effect_size**2)))
            has_power = sample_size >= min_sample

        entry: dict[str, Any] = {
            "completion_rate": round(rate, 4),
            "ci_lower": round(ci_lower, 4),
            "ci_upper": round(ci_upper, 4),
            "n": n,
            "resolved": k,
            "sample_size": sample_size,
            "total_count": total_count,
        }
        if has_power is not None:
            entry["has_power"] = has_power

        results[str(borough)] = entry
        rows.append({"borough": str(borough), **entry})

    all_n = sum(r["total_count"] for r in results.values())
    all_k = sum(r["resolved"] for r in results.values())
    overall = all_k / all_n if all_n > 0 else 0.0

    results["comparison_table"] = pd.DataFrame(rows)
    results["overall_completion_rate"] = round(overall, 4)
    return results
