import pandas as pd
import pytest

from socrata_toolkit.integrations.excel import (
    ExcelWorkbookBuilder,
    averageif,
    countif,
    create_pivot_table,
    index_match,
    sumif,
    vlookup,
)


def _sample():
    return pd.DataFrame({
        "borough": ["MANHATTAN", "MANHATTAN", "BROOKLYN", "QUEENS"],
        "violations": [5, 3, 8, 2],
        "status": ["Pending", "Complete", "Pending", "Pending"],
        "location_id": ["L1", "L2", "L3", "L4"],
    })


def test_create_pivot_table():
    df = _sample()
    pivot = create_pivot_table(df, rows="borough", values="violations", aggfunc="sum")
    assert "borough" in pivot.columns
    assert len(pivot) >= 3  # 3 boroughs + Grand Total


def test_vlookup():
    source = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})
    lookup = pd.DataFrame({"id": [1, 2, 4], "score": [90, 80, 70]})
    result = vlookup(source, lookup, "id", "id", "score", default=0)
    assert "score" in result.columns
    assert result.loc[0, "score"] == 90
    assert result.loc[2, "score"] == 0  # id=3 not in lookup


def test_index_match():
    df = pd.DataFrame({"name": ["alice", "bob"], "score": [95, 80]})
    assert index_match(df, "name", "alice", "score") == 95
    assert index_match(df, "name", "charlie", "score", default=-1) == -1


def test_sumif():
    df = _sample()
    assert sumif(df, "borough", "MANHATTAN", "violations") == 8


def test_countif():
    df = _sample()
    assert countif(df, "status", "Pending") == 3


def test_averageif():
    df = _sample()
    avg = averageif(df, "borough", "MANHATTAN", "violations")
    assert avg == 4.0


def test_workbook_builder_data_sheet(tmp_path):
    df = _sample()
    path = str(tmp_path / "test.xlsx")
    builder = ExcelWorkbookBuilder()
    builder.add_data_sheet("Data", df)
    builder.save(path)
    loaded = pd.read_excel(path, sheet_name="Data")
    assert len(loaded) == 4


def test_workbook_builder_pivot_sheet(tmp_path):
    df = _sample()
    path = str(tmp_path / "test.xlsx")
    builder = ExcelWorkbookBuilder()
    builder.add_data_sheet("Raw", df)
    builder.add_pivot_sheet("Pivot", df, rows="borough", values="violations")
    builder.save(path)
    loaded = pd.read_excel(path, sheet_name="Pivot")
    assert len(loaded) >= 3


def test_workbook_builder_formula_column(tmp_path):
    df = _sample()
    path = str(tmp_path / "test.xlsx")
    builder = ExcelWorkbookBuilder()
    builder.add_data_sheet("Data", df)
    builder.add_formula_column("Data", "calc", "=B{row}*2")
    builder.save(path)
    # Formula column should be added
    assert "Data" in builder.sheet_names()


def test_workbook_builder_sheet_data():
    df = _sample()
    builder = ExcelWorkbookBuilder()
    builder.add_data_sheet("Test", df)
    assert builder.sheet_data("Test") is not None
    assert builder.sheet_data("Missing") is None
