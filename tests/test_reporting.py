import json

import pandas as pd
import pytest

from socrata_toolkit.reporting import (
    Report,
    generate_contract_report,
    generate_inquiry_response,
    generate_program_report,
)


def _sample_contracts():
    return pd.DataFrame({
        "contract_id": ["C1", "C2", "C3"],
        "borough": ["MANHATTAN", "BROOKLYN", "QUEENS"],
        "planned_sqft": [1000, 2000, 500],
        "actual_sqft": [800, 1500, 500],
        "planned_spend": [50000, 100000, 25000],
        "actual_spend": [45000, 110000, 24000],
        "status": ["in_progress", "in_progress", "complete"],
        "address": ["123 Main St", "456 Oak Ave", "789 Elm Blvd"],
    })


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
    from socrata_toolkit.program_metrics import MetricsTracker
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
