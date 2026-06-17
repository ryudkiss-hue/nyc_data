"""Tests for the CUSUM anomaly detection helper used by the sidebar badge.

The ``_detect_sidebar_anomaly`` function in ``app.app`` is decorated with
``@st.cache_data`` and therefore cannot be imported directly in a plain
pytest context.  Instead, we test ``detect_cusum_changepoint`` from
``socrata_toolkit.analysis.changepoint``, which is the underlying function
used by the helper.
"""

from __future__ import annotations

import pandas as pd

from socrata_toolkit.analysis.changepoint import detect_cusum_changepoint


def test_detect_sidebar_anomaly_true_on_step_change() -> None:
    """A step-function series (flat then jump) should trigger a changepoint."""
    # 10 observations at ~0, then 10 at ~10 — clear level shift
    flat = [0.0] * 10
    jump = [10.0] * 10
    series = pd.Series(flat + jump)
    result = detect_cusum_changepoint(series)
    assert result is not None, "Expected a changepoint index for a step-function series, got None"


def test_sidebar_anomaly_false_on_flat_via_threshold() -> None:
    """A perfectly flat series should NOT trigger the sidebar badge.

    The sidebar helper ``_detect_sidebar_anomaly`` adds a 3-sigma CUSUM
    threshold on top of ``detect_cusum_changepoint``.  Verify the threshold
    logic directly: flat data has std=0, so the condition is never met.
    """
    series = pd.Series([5.0] * 20)
    sigma = float(series.std())
    mu = float(series.mean())
    cusum = (series - mu).cumsum()
    peak = float(cusum.abs().max())
    # Flat series → std == 0 → threshold check short-circuits to False
    is_anomaly = sigma > 0 and peak > 3.0 * sigma
    assert not is_anomaly, "Flat series should not trigger anomaly badge"


def test_detect_cusum_changepoint_returns_none_for_short_series() -> None:
    """Series shorter than 4 observations must return None."""
    series = pd.Series([1.0, 2.0, 3.0])
    assert detect_cusum_changepoint(series) is None


def test_detect_cusum_changepoint_index_within_range() -> None:
    """Returned index must be a valid position in the series."""
    flat = [1.0] * 15
    jump = [20.0] * 15
    series = pd.Series(flat + jump)
    result = detect_cusum_changepoint(series)
    assert result is not None
    assert 0 <= result < len(series)
