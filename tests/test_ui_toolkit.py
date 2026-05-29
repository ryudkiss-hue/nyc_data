"""Tests for the UI toolkit: palettes, export helpers, url_state."""

from __future__ import annotations

import io
import zipfile

import pandas as pd
import pytest

from app.ui import palettes
from app.utils import export


# ---------------------------------------------------------------------------
# palettes
# ---------------------------------------------------------------------------
def test_categorical_returns_requested_count():
    assert len(palettes.categorical(3)) == 3
    assert len(palettes.categorical(5)) == 5


def test_categorical_cycles_when_exceeding_palette():
    n = len(palettes.AGENCY_CATEGORICAL) + 3
    out = palettes.categorical(n)
    assert len(out) == n
    # cycles back to the first color
    assert out[len(palettes.AGENCY_CATEGORICAL)] == palettes.AGENCY_CATEGORICAL[0]


def test_severity_color_known_and_fallback():
    assert palettes.severity_color("critical") == "#EF4444"
    assert palettes.severity_color("OK") == "#10B981"
    assert palettes.severity_color("nonsense") == palettes.SEMANTIC["neutral"]


def test_okabe_ito_has_eight_distinct_colors():
    assert len(palettes.OKABE_ITO) == 8
    assert len(set(palettes.OKABE_ITO)) == 8


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------
@pytest.fixture
def frames():
    return {
        "alpha": pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]}),
        "beta": pd.DataFrame({"c": [4.0, 5.0]}),
    }


def test_to_csv_bytes_roundtrip(frames):
    raw = export.to_csv_bytes(frames["alpha"])
    assert isinstance(raw, bytes)
    back = pd.read_csv(io.BytesIO(raw))
    assert list(back.columns) == ["a", "b"]
    assert len(back) == 3


def test_to_json_bytes_is_records(frames):
    raw = export.to_json_bytes(frames["alpha"])
    assert raw.strip().startswith(b"[")


def test_zip_bundle_contains_all_datasets_plus_manifest(frames):
    raw = export.to_zip_bundle(frames, fmt="csv")
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = zf.namelist()
    assert any("alpha" in n for n in names)
    assert any("beta" in n for n in names)
    assert "manifest.json" in names


def test_zip_bundle_json_format(frames):
    raw = export.to_zip_bundle(frames, fmt="json")
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        assert any(n.endswith(".json") and "alpha" in n for n in zf.namelist())


def test_summary_table_shape(frames):
    summary = export.summary_table(frames)
    assert set(summary.columns) == {"Dataset", "Rows", "Columns", "Memory (KB)"}
    assert len(summary) == 2
    alpha_row = summary[summary["Dataset"] == "alpha"].iloc[0]
    assert alpha_row["Rows"] == 3
    assert alpha_row["Columns"] == 2


def test_excel_bytes_or_none(frames):
    # Should return bytes if an engine is installed, else None — never raise
    result = export.to_excel_bytes(frames)
    assert result is None or isinstance(result, bytes)
