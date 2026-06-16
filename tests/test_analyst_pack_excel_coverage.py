"""Coverage test for analyst.pack._dataframe_to_excel autofilter fallback."""

from __future__ import annotations
import pytest


from unittest.mock import patch

import pandas as pd


class TestDataframeToExcel:
    def test_normal_write(self, tmp_path):
        from socrata_toolkit.analyst.pack import _dataframe_to_excel

        df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        out = tmp_path / "out.xlsx"
        _dataframe_to_excel(df, out)
        assert out.exists()
        assert len(pd.read_excel(out)) == 2

    def test_autofilter_typeerror_fallback(self, tmp_path):
        from socrata_toolkit.analyst.pack import _dataframe_to_excel

        df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        out = tmp_path / "out.xlsx"
        original = pd.DataFrame.to_excel
        calls = {"n": 0}

        def _raise_once(self, *args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise TypeError("unexpected keyword argument 'autofilter'")
            return original(self, *args, **kwargs)

        with patch.object(pd.DataFrame, "to_excel", _raise_once):
            _dataframe_to_excel(df, out)
        # Fallback path wrote via openpyxl Workbook
        assert out.exists()
        result = pd.read_excel(out)
        assert list(result.columns) == ["a", "b"]
        assert len(result) == 2

    def test_other_typeerror_reraised(self, tmp_path):
        import pytest

        from socrata_toolkit.analyst.pack import _dataframe_to_excel

        df = pd.DataFrame({"a": [1]})
        with patch.object(pd.DataFrame, "to_excel", side_effect=TypeError("some other error")):
            with pytest.raises(TypeError):
                _dataframe_to_excel(df, tmp_path / "out.xlsx")
