"""Tests for interactive exploration components and explore helpers."""

from __future__ import annotations
import pytest


import sys
from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip("dash")
from dash import html

ROOT = Path(__file__).resolve().parents[1]
LEGACY_DASH = ROOT / "legacy_archive"
for p in (str(ROOT / "src"), str(ROOT), str(LEGACY_DASH)):
    if p not in sys.path:
        sys.path.insert(0, p)

from socrata_toolkit.analyst.explore import (
    borough_bar_counts,
    filter_kpi_metrics,
    normalize_weights,
    preview_priority,
    profile_weight_snippet,
)
from socrata_toolkit.engineering.construction_list import DEFAULT_PRIORITY_WEIGHTS

pytest.importorskip("dash")
from dash_app.components.interactive import param_slider, tip_card  # noqa: E402


def test_interactive_components_import():
    card = tip_card("Title", "Body text", id="test-tip")
    slider = param_slider("Weight", 0, 1, 0.1, 0.5, "test-slider", aria_label="Weight")
    assert card is not None
    assert slider is not None


def test_normalize_weights_sums_to_one():
    w = normalize_weights(0.3, 0.2, 0.15, 0.15, 0.1, 0.1)
    assert abs(sum(w.values()) - 1.0) < 0.01
    assert set(w.keys()) == set(DEFAULT_PRIORITY_WEIGHTS.keys())


def test_preview_priority_with_fixture():
    df = pd.DataFrame(
        {
            "location_id": ["L1", "L2"],
            "borough": ["MANHATTAN", "BROOKLYN"],
            "severity_rating": [9, 3],
            "pedestrian_volume": [5000, 500],
            "issued_date": ["2020-01-01", "2024-01-01"],
            "ada_flag": [True, False],
            "smart_spine": [True, False],
            "complaint_count": [5, 0],
        }
    )
    result = preview_priority(df, top_n=1)
    assert len(result) == 1
    assert "_priority_score" in result.columns
    assert result.iloc[0]["location_id"] == "L1"


def test_borough_bar_counts():
    df = pd.DataFrame({"borough": ["A", "A", "B"], "_priority_score": [0.9, 0.8, 0.5]})
    counts = borough_bar_counts(df)
    assert "A" in counts
    assert counts["A"] > counts["B"]


def test_filter_kpi_metrics():
    metrics = [
        {"name": "Open backlog", "value": 10, "target": 5, "status": "red"},
        {"name": "CPI ratio", "value": 0.9, "target": 1.0, "status": "yellow"},
    ]
    filtered = filter_kpi_metrics(metrics, categories=["budget"])
    assert len(filtered) == 1
    assert "CPI" in filtered[0]["name"]


def test_profile_weight_snippet():
    w = normalize_weights(0.3, 0.2, 0.15, 0.15, 0.1, 0.1)
    snippet = profile_weight_snippet(w)
    assert "priority_weights" in snippet
    assert "severity" in snippet


def test_construction_page_imports():
    import dash_app.app  # noqa: F401
    from dash_app.pages import construction

    assert construction.layout is not None


def test_shell_helpers():
    from dash_app.components.shell import empty_state, page_shell

    shell = page_shell("Test", "Subtitle", page_key="home", children=[html.Div("body")])
    assert len(shell) == 1
    assert shell[0].className == "nyc-page-shell"
    empty = empty_state("No data")
    assert empty is not None
