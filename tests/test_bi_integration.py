import json

import pandas as pd
import pytest

from socrata_toolkit.integrations.bi import (
    SlideContent,
    create_presentation,
    export_bi_package,
    export_for_powerbi,
    export_for_tableau,
)


def _sample():
    return pd.DataFrame({
        "borough": ["MANHATTAN", "BROOKLYN", "QUEENS"],
        "violations": [5, 8, 2],
        "severity_rating": [7, 9, 3],
        "status": ["Pending Repair", "Complete", "Pending Repair"],
        "inspection_date": ["2024-01-15", "2024-03-20", "2024-06-10"],
    })


def test_export_for_tableau(tmp_path):
    df = _sample()
    result = export_for_tableau(
        df, str(tmp_path / "tableau"),
        date_columns=["inspection_date"],
        geo_columns={"borough": "State/Province"},
    )
    assert result.row_count == 3
    assert result.column_count == 5
    # Check CSV exists
    loaded = pd.read_csv(result.csv_path)
    assert len(loaded) == 3
    # Check metadata
    meta = json.loads(open(result.metadata_path).read())
    assert meta["row_count"] == 3
    geo_col = [c for c in meta["columns"] if c["name"] == "borough"][0]
    assert geo_col["geographic_role"] == "State/Province"


def test_export_for_powerbi(tmp_path):
    df = _sample()
    result = export_for_powerbi(
        df, str(tmp_path / "powerbi"),
        date_columns=["inspection_date"],
    )
    assert result.row_count == 3
    assert len(result.dax_measures) >= 1
    # Check model file
    model = json.loads(open(result.model_path).read())
    assert "measures" in model
    assert "columns" in model


def test_create_presentation_html(tmp_path):
    slides = [
        SlideContent(title="Overview", body="Program status overview", data={"Total": 100}),
        SlideContent(title="Details", body="Detailed analysis"),
    ]
    path = str(tmp_path / "report.html")
    result = create_presentation(slides, path, title="Test Report")
    content = open(result).read()
    assert "<h1>Test Report</h1>" in content
    assert "Overview" in content


def test_export_bi_package(tmp_path):
    df = _sample()
    paths = export_bi_package(df, str(tmp_path / "bi_pkg"), dataset_name="test_data")
    assert "csv" in paths
    assert "json" in paths
    assert "schema" in paths
    loaded = pd.read_csv(paths["csv"])
    assert len(loaded) == 3
    schema = json.loads(open(paths["schema"]).read())
    assert schema["row_count"] == 3
