"""Tests for QA checklist, reproducibility keys, and forecast validation."""

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest


def test_run_preflight_passes_clean_data():
    from socrata_toolkit.analysis.qa_checklist import run_preflight

    df = pd.DataFrame({"a": range(50), "b": range(50)})
    report = run_preflight(df, "violations", min_rows=10)
    assert not report.blocked
    assert any(c.passed for c in report.checks)


def test_run_preflight_blocks_too_few_rows():
    from socrata_toolkit.analysis.qa_checklist import run_preflight

    df = pd.DataFrame({"a": range(3)})
    report = run_preflight(df, "violations", min_rows=10)
    assert report.blocked


def test_run_preflight_stale_data():
    from socrata_toolkit.analysis.qa_checklist import run_preflight

    df = pd.DataFrame({"a": range(50)})
    stale_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    report = run_preflight(df, "violations", freshness_hours=24, fetch_timestamp=stale_ts)
    freshness_check = next(c for c in report.checks if c.check_name == "data_freshness")
    assert not freshness_check.passed


def test_run_preflight_missing_columns():
    from socrata_toolkit.analysis.qa_checklist import run_preflight

    df = pd.DataFrame({"a": range(50)})
    report = run_preflight(df, "violations", required_columns=["a", "b", "c"])
    col_check = next(c for c in report.checks if c.check_name == "required_columns")
    assert not col_check.passed
    assert report.blocked


def test_run_preflight_summary_string():
    from socrata_toolkit.analysis.qa_checklist import run_preflight

    df = pd.DataFrame({"a": range(50)})
    report = run_preflight(df, "violations")
    s = report.summary()
    assert "OK" in s or "BLOCKED" in s


def test_make_run_key_deterministic():
    from socrata_toolkit.analysis.reproducibility import make_run_key

    ts = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    k1 = make_run_key("borough_comparison", "violations", 500, ts, {"alpha": 0.05})
    k2 = make_run_key("borough_comparison", "violations", 500, ts, {"alpha": 0.05})
    assert k1.run_key == k2.run_key


def test_make_run_key_differs_on_params():
    from socrata_toolkit.analysis.reproducibility import make_run_key

    ts = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    k1 = make_run_key("test", "violations", 500, ts, {"alpha": 0.05})
    k2 = make_run_key("test", "violations", 500, ts, {"alpha": 0.10})
    assert k1.run_key != k2.run_key


def test_make_run_key_footer():
    from socrata_toolkit.analysis.reproducibility import make_run_key

    ts = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    k = make_run_key("test", "violations", 100, ts)
    footer = k.to_footer()
    assert "Run:" in footer
    assert "Analysis: test" in footer


def test_validate_forecasts_basic():
    from socrata_toolkit.analysis.forecast_validation import validate_forecasts

    forecasts = pd.DataFrame({"id": [1, 2, 3], "predicted": [10.0, 20.0, 30.0]})
    actuals = pd.DataFrame({"id": [1, 2, 3], "actual": [11.0, 19.0, 31.0]})
    result = validate_forecasts(forecasts, actuals, "predicted", "actual", "id")
    assert result.n_forecasts == 3
    assert abs(result.mae - 1.0) < 0.01
    assert abs(result.bias) < 0.5


def test_validate_forecasts_ci_coverage():
    from socrata_toolkit.analysis.forecast_validation import validate_forecasts

    forecasts = pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "predicted": [10.0] * 5,
            "lower": [8.0] * 5,
            "upper": [12.0] * 5,
        }
    )
    actuals = pd.DataFrame({"id": [1, 2, 3, 4, 5], "actual": [9.0, 11.0, 10.0, 10.5, 9.5]})
    result = validate_forecasts(
        forecasts, actuals, "predicted", "actual", "id", ci_lower_col="lower", ci_upper_col="upper"
    )
    assert result.within_ci_rate == 1.0


def test_validate_forecasts_empty_join_raises():
    from socrata_toolkit.analysis.forecast_validation import validate_forecasts

    forecasts = pd.DataFrame({"id": [1, 2], "predicted": [10.0, 20.0]})
    actuals = pd.DataFrame({"id": [3, 4], "actual": [11.0, 19.0]})
    with pytest.raises(ValueError, match="No matching"):
        validate_forecasts(forecasts, actuals, "predicted", "actual", "id")


def test_summarize_forecast_accuracy():
    from socrata_toolkit.analysis.forecast_validation import (
        ForecastValidationResult,
        summarize_forecast_accuracy,
    )

    r = ForecastValidationResult(
        "x", "score", 100, mae=2.5, rmse=3.1, bias=-0.5, within_ci_rate=0.92
    )
    s = summarize_forecast_accuracy(r)
    assert "under-estimated" in s
    assert "MAE=2.50" in s
    assert "92%" in s
