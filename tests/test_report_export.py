"""Unit tests for app.utils.report_export."""

from __future__ import annotations

from app.utils.report_export import build_excel_report, build_pdf_report

_SAMPLE_SECTIONS: dict[str, list[dict]] = {
    "Inspections": [
        {"Borough": "Manhattan", "Count": 120, "Status": "Open"},
        {"Borough": "Brooklyn", "Count": 85, "Status": "Closed"},
    ],
    "Summary": [
        {"Metric": "Total units", "Value": 205},
        {"Metric": "Completion rate", "Value": "58.5%"},
    ],
}

def test_build_excel_report_returns_bytes() -> None:
    result = build_excel_report("SIM Inspection Report", _SAMPLE_SECTIONS)
    assert isinstance(result, bytes)
    assert len(result) > 0
    # .xlsx files begin with the ZIP magic bytes "PK"
    assert result[:2] == b"PK", "Expected .xlsx (ZIP) magic bytes 'PK'"

def test_build_excel_report_empty_sections() -> None:
    """An empty sections dict should still produce valid .xlsx bytes."""
    result = build_excel_report("Empty Report", {})
    assert isinstance(result, bytes)
    assert len(result) > 0

def test_build_excel_report_empty_rows() -> None:
    """A section with no rows should not raise."""
    result = build_excel_report("Report", {"Empty Sheet": []})
    assert isinstance(result, bytes)
    assert len(result) > 0

def test_build_pdf_report_returns_none_or_bytes() -> None:
    result = build_pdf_report("SIM Inspection Report", _SAMPLE_SECTIONS)
    assert result is None or isinstance(result, bytes), (
        "build_pdf_report must return None (WeasyPrint missing) or bytes"
    )
    if isinstance(result, bytes):
        assert len(result) > 0
        # PDF files start with the magic bytes %PDF
        assert result[:4] == b"%PDF", "Expected PDF magic bytes '%PDF'"
