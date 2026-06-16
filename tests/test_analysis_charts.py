import pytest

import pytest

pytest.importorskip("plotly", reason="plotly required for chart tests")

import pandas as pd
import plotly.graph_objects as go

from socrata_toolkit.analysis import DashboardSummary, DataProfile
from socrata_toolkit.core import COLOR_GREEN, COLOR_RED, COLOR_YELLOW
from socrata_toolkit.viz import (
    data_completeness_chart,
    metric_status_pie_chart,
    plot_geospatial_compliance_map,
)


def test_data_completeness_chart_with_data():
    """
    Tests that data_completeness_chart generates a valid Plotly figure
    with correctly sorted data when given a populated DataProfile.
    """
    # 1. Setup: Create a sample DataProfile
    profile = DataProfile(
        row_count=100,
        column_count=3,
        columns=[
            {"name": "full_column", "type": "int64", "null_pct": 0.0, "unique": 100, "sample": "1"},
            {
                "name": "half_empty_column",
                "type": "object",
                "null_pct": 50.0,
                "unique": 50,
                "sample": "abc",
            },
            {
                "name": "mostly_full_column",
                "type": "float64",
                "null_pct": 10.0,
                "unique": 90,
                "sample": "3.14",
            },
        ],
        null_counts={},
        quality_score=80,
        warnings=[],
        numeric_summary={},
    )

    # 2. Execution
    fig = data_completeness_chart(profile, title="Test Completeness Chart")

    # 3. Assertions
    assert isinstance(fig, go.Figure)
    assert fig.layout.title.text == "Test Completeness Chart"

    # Check that the data is sorted correctly (ascending completeness)
    # Completeness = 100 - null_pct
    # half_empty_column: 50%
    # mostly_full_column: 90%
    # full_column: 100%
    expected_y_order = ("half_empty_column", "mostly_full_column", "full_column")
    expected_x_values = (50.0, 90.0, 100.0)

    assert len(fig.data) == 1
    chart_data = fig.data[0]
    assert chart_data.type == "bar"
    assert chart_data.orientation == "h"
    assert tuple(chart_data.y) == expected_y_order
    assert tuple(chart_data.x) == expected_x_values

    # Check layout properties
    assert fig.layout.xaxis.range == (0, 100)
    assert "Completeness (%)" in fig.layout.xaxis.title.text


def test_data_completeness_chart_empty_profile():
    """
    Tests that data_completeness_chart returns an empty figure
    when the DataProfile has no columns.
    """
    # 1. Setup: Create an empty DataProfile
    profile = DataProfile(
        row_count=0,
        column_count=0,
        columns=[],
        null_counts={},
        quality_score=0,
        warnings=[],
        numeric_summary={},
    )

    # 2. Execution
    fig = data_completeness_chart(profile)

    # 3. Assertions
    assert isinstance(fig, go.Figure)
    # An empty figure created with go.Figure() has no data traces
    assert len(fig.data) == 0


def test_metric_status_pie_chart_all_statuses():
    """
    Tests that metric_status_pie_chart generates a valid pie chart
    when all metric statuses (green, yellow, red) are present.
    """
    # 1. Setup
    summary = DashboardSummary(
        metrics=[],
        overall_health="red",
        green_count=10,
        yellow_count=5,
        red_count=2,
    )

    # 2. Execution
    fig = metric_status_pie_chart(summary, title="Test Pie Chart")

    # 3. Assertions
    assert isinstance(fig, go.Figure)
    assert fig.layout.title.text == "Test Pie Chart"
    assert len(fig.data) == 1

    chart_data = fig.data[0]
    assert chart_data.type == "pie"

    # The function filters for non-zero values, so we check the contents.
    # The order might not be guaranteed, so check as sets.
    expected_labels = {"Green (On Target)", "Yellow (Warning)", "Red (Alert)"}
    expected_values = {10, 5, 2}
    expected_colors = {COLOR_GREEN, COLOR_YELLOW, COLOR_RED}

    assert set(chart_data.labels) == expected_labels
    assert set(chart_data.values) == expected_values
    assert set(chart_data.marker.colors) == expected_colors

    # Check that the red slice is pulled (exploded)
    # Find the index of the red slice to check its 'pull' value
    labels_list = list(chart_data.labels)
    red_index = labels_list.index("Red (Alert)")
    assert chart_data.pull[red_index] > 0
    green_index = labels_list.index("Green (On Target)")
    assert chart_data.pull[green_index] == 0


def test_metric_status_pie_chart_some_zero_counts():
    """
    Tests that the pie chart correctly omits slices for statuses with zero counts.
    """
    # 1. Setup: Only green and red metrics
    summary = DashboardSummary(
        metrics=[],
        overall_health="red",
        green_count=12,
        yellow_count=0,
        red_count=3,
    )

    # 2. Execution
    fig = metric_status_pie_chart(summary)

    # 3. Assertions
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1

    chart_data = fig.data[0]
    # Should only have two slices
    assert len(chart_data.labels) == 2
    assert set(chart_data.labels) == {"Green (On Target)", "Red (Alert)"}
    assert set(chart_data.values) == {12, 3}
    assert set(chart_data.marker.colors) == {COLOR_GREEN, COLOR_RED}


def test_metric_status_pie_chart_all_zero_counts():
    """
    Tests that an empty state with an annotation is shown when all metric counts are zero.
    """
    # 1. Setup
    summary = DashboardSummary(
        metrics=[],
        overall_health="unknown",
        green_count=0,
        yellow_count=0,
        red_count=0,
    )

    # 2. Execution
    fig = metric_status_pie_chart(summary)

    # 3. Assertions
    assert isinstance(fig, go.Figure)
    # Should have no data traces
    assert len(fig.data) == 0
    # Should have an annotation
    assert len(fig.layout.annotations) > 0
    assert "No metric data" in fig.layout.annotations[0].text


def test_plot_geospatial_compliance_map_with_mixed_data():
    """
    Tests the map generation with points both inside and outside NYC bounds.
    """
    # 1. Setup
    data = {
        "latitude": [40.7128, 40.5, 40.8, None],  # NYC, outside, inside, NaN
        "longitude": [-74.0060, -74.0, -73.9, None],  # NYC, inside, inside, NaN
        "id": [1, 2, 3, 4],
    }
    df = pd.DataFrame(data)

    # 2. Execution
    fig = plot_geospatial_compliance_map(df, title="Geo Test")

    # 3. Assertions
    assert isinstance(fig, go.Figure)
    assert fig.layout.title.text == "Geo Test"
    # Should create two traces: one for "In Bounds" and one for "Out of Bounds"
    assert len(fig.data) == 2

    trace_names = {trace.name for trace in fig.data}
    assert trace_names == {"In Bounds", "Out of Bounds"}

    for trace in fig.data:
        if trace.name == "In Bounds":
            # Points (40.7128, -74.0060) and (40.8, -73.9) are in bounds
            assert len(trace.lat) == 2
        elif trace.name == "Out of Bounds":
            # Point (40.5, -74.0) is out of bounds
            assert len(trace.lat) == 1


def test_plot_geospatial_compliance_map_empty_and_missing_cols():
    """
    Tests edge cases: empty dataframe, missing columns, and all-NaN columns.
    """
    # Empty DataFrame
    fig_empty = plot_geospatial_compliance_map(pd.DataFrame())
    assert isinstance(fig_empty, go.Figure)
    assert len(fig_empty.data) == 0

    # Missing columns
    fig_missing_cols = plot_geospatial_compliance_map(pd.DataFrame({"a": [1]}))
    assert isinstance(fig_missing_cols, go.Figure)
    assert len(fig_missing_cols.data) == 0

    # All-NaN columns
    df_nan = pd.DataFrame({"latitude": [None, None], "longitude": [None, None]})
    fig_nan = plot_geospatial_compliance_map(df_nan)
    assert isinstance(fig_nan, go.Figure)
    assert len(fig_nan.data) == 0
