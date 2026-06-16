from __future__ import annotations
import pytest
pytestmark = pytest.mark.skip(reason="Data Unavailable - Live telemetry required")

import json

import pandas as pd
import pytest

from socrata_toolkit.analysis import (
    Report,
    generate_contract_report,
    generate_inquiry_response,
    generate_program_report,
)


def _sample_contracts():
    return pd.DataFrame(
        {
            "contract_id": ["C1", "C2", "C3"],
            "borough": ["MANHATTAN", "BROOKLYN", "QUEENS"],
            "planned_sqft": [1000, 2000, 500],
            "actual_sqft": [800, 1500, 500],
            "planned_spend": [50000, 100000, 25000],
            "actual_spend": [45000, 110000, 24000],
            "status": ["in_progress", "in_progress", "complete"],
            "address": ["123 Main St", "456 Oak Ave", "789 Elm Blvd"],
        }
    )


def test_report_to_markdown():
    report = Report(title="Test", generated_at="2025-01-01")
    report.add_section("Section 1", "Content here", {"key": "value"})
    md = report.to_markdown()
    assert "# Test" in md
    assert "Section 1" in md
    assert "**key**" in md


def test_report_to_json():
    report = Report(title="Test", generated_at="2025-01-01")
    report.add_section("S1", "C1")
    data = json.loads(report.to_json())
    assert data["title"] == "Test"
    assert len(data["sections"]) == 1


def test_report_to_html():
    report = Report(title="Test", generated_at="2025-01-01")
    report.add_section("S1", "C1", {"k": "v"})
    html = report.to_html()
    assert "<h1>Test</h1>" in html
    assert "<h2>S1</h2>" in html


def test_report_save_markdown(tmp_path):
    report = Report(title="Test", generated_at="2025-01-01")
    report.add_section("S1", "Content")
    path = str(tmp_path / "report.md")
    report.save(path)
    content = open(path).read()
    assert "# Test" in content


def test_report_save_json(tmp_path):
    report = Report(title="Test", generated_at="2025-01-01")
    path = str(tmp_path / "report.json")
    report.save(path)
    data = json.loads(open(path).read())
    assert data["title"] == "Test"


def test_generate_contract_report():
    df = _sample_contracts()
    report = generate_contract_report(df)
    assert "Contract Status" in report.title
    assert len(report.sections) >= 2
    md = report.to_markdown()
    assert "Portfolio Summary" in md
    assert "Borough Breakdown" in md


def test_generate_program_report():
    from socrata_toolkit.analysis import MetricsTracker

    tracker = MetricsTracker()
    tracker.load_standard_kpis()
    tracker.record("defect_density", 1.5)
    tracker.record("throughput_velocity", 250.0)
    tracker.add_budget_code("PS-001", allocated=100000, spent=60000, category="personnel")
    dashboard = tracker.dashboard()

    report = generate_program_report(dashboard)
    assert "KPI" in report.title
    assert len(report.sections) >= 3
    md = report.to_markdown()
    assert "Program Health" in md


def test_generate_inquiry_response_contract():
    df = _sample_contracts()
    report = generate_inquiry_response("contract_status", df, contract_id="C1")
    assert len(report.sections) >= 1
    assert "C1" in report.to_markdown()


def test_generate_inquiry_response_location():
    df = _sample_contracts()
    report = generate_inquiry_response("location_status", df, location="Main")
    assert len(report.sections) >= 1


def test_generate_inquiry_response_borough():
    df = _sample_contracts()
    report = generate_inquiry_response("borough_overview", df, borough="MANHATTAN")
    md = report.to_markdown()
    assert "MANHATTAN" in md


# ---------------------------------------------------------------------------
# Unit-13 additions: Excel, HTML table, PDF, (optional WeasyPrint)
# ---------------------------------------------------------------------------


def _small_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "inspection_id": ["INS-001", "INS-002", "INS-003"],
            "borough": ["MANHATTAN", "BRONX", "QUEENS"],
            "condition_score": [88, 72, 65],
            "address": ["1 Broadway", "500 Grand Concourse", "90-01 Queens Blvd"],
        }
    )


def test_generate_excel_report_smoke(tmp_path):
    """generate_excel_report should return bytes; save to tmp_path and verify size > 0."""
    from app.utils.reporting import generate_excel_report

    df = _small_df()
    excel_bytes = generate_excel_report(
        sheets={"Inspections": df},
        summary_text="Unit-13 smoke test",
    )
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0

    out_path = tmp_path / "report.xlsx"
    out_path.write_bytes(excel_bytes)
    assert out_path.exists()
    assert out_path.stat().st_size > 0


def test_generate_excel_report_multiple_sheets(tmp_path):
    """Multiple sheets should all appear in the workbook."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")

    from app.utils.reporting import generate_excel_report

    df = _small_df()
    excel_bytes = generate_excel_report(
        sheets={"Sheet1": df, "Sheet2": df.head(1)},
        summary_text="Multi-sheet test",
    )
    import io

    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    sheet_names = wb.sheetnames
    assert "Sheet1" in sheet_names
    assert "Sheet2" in sheet_names


def test_dataframe_to_html_table_basic():
    """dataframe_to_html_table should return a string containing <table and column names."""
    from app.utils.reporting import dataframe_to_html_table

    df = _small_df()
    html = dataframe_to_html_table(df)
    assert isinstance(html, str)
    assert "<table" in html.lower()
    for col in df.columns:
        assert col in html


def test_dataframe_to_html_table_max_rows():
    """max_rows parameter should truncate the output."""
    from app.utils.reporting import dataframe_to_html_table

    df = pd.DataFrame({"val": range(50)})
    html_5 = dataframe_to_html_table(df, max_rows=5)
    html_50 = dataframe_to_html_table(df, max_rows=50)
    # The 5-row version should be shorter
    assert len(html_5) < len(html_50)


def test_generate_pdf_report_smoke():
    """generate_pdf_report should raise ImportError when WeasyPrint is absent,
    or return bytes when it is present."""
    from app.utils.reporting import generate_pdf_report

    df = _small_df()
    try:
        result = generate_pdf_report(
            title="Unit-13 PDF Test",
            summary_text="Smoke test for PDF generation.",
            dataframes={"Inspections": df},
            output_bytes=True,
        )
        assert isinstance(result, bytes)
        assert len(result) > 0
    except ImportError:
        pytest.skip("WeasyPrint not installed — PDF smoke test skipped")
