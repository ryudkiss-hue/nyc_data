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
