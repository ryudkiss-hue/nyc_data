import pandas as pd

from socrata_toolkit.analysis.core import profile_dataframe, quality_report


def test_profile_dataframe_basic():
    df = pd.DataFrame({"a": [1, 2, None], "b": ["x", "y", "y"]})
    p = profile_dataframe(df)
    assert p.row_count == 3
    assert p.column_count == 2
    assert p.null_counts["a"] == 1


def test_quality_report_duplicates():
    df = pd.DataFrame({"id": [1, 1, 2], "v": [10, 10, 20]})
    q = quality_report(df, ["id"])
    assert q["duplicate_rows"] == 0
    assert q["duplicate_keys"]["id"] == 1
