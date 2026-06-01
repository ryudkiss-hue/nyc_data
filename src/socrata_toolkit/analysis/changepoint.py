"""Pure CUSUM changepoint detection — no UI dependencies."""
from __future__ import annotations

import pandas as pd


def detect_cusum_changepoint(series: pd.Series) -> int | None:
    """Return the index of the most likely level-shift in *series* via CUSUM.

    Returns ``None`` when the series is too short (< 4 observations).
    """
    if len(series) < 4:
        return None
    mu = series.mean()
    cusum = (series - mu).cumsum()
    return int(cusum.abs().idxmax())
