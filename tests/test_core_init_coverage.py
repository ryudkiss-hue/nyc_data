"""Coverage tests for socrata_toolkit.core package-level helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

class TestDuckDBExporter:
    def test_context_manager_closes(self):
        from socrata_toolkit.core import DuckDBExporter

        mgr = MagicMock()
        with patch("socrata_toolkit.core.DuckDBManager", return_value=mgr):
            with DuckDBExporter(":memory:") as exp:
                assert exp is not None
            mgr.close.assert_called_once()

class TestSearchNycDatasets:
    def test_returns_dataframe(self):
        from socrata_toolkit.core import search_nyc_datasets
        from socrata_toolkit.core.models import SearchResult

        result = SearchResult(
            name="Test", description="d", domain="data.cityofnewyork.us",
            fourfour="abc1-2345", page_views_last_month=10, category="cat", tags=["t"],
        )
        with patch("socrata_toolkit.core.SocrataClient") as mock_cls:
            mock_cls.return_value.search.return_value = [result]
            df = search_nyc_datasets("sidewalk")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert df.iloc[0]["fourfour"] == "abc1-2345"

    def test_empty_results(self):
        from socrata_toolkit.core import search_nyc_datasets

        with patch("socrata_toolkit.core.SocrataClient") as mock_cls:
            mock_cls.return_value.search.return_value = []
            df = search_nyc_datasets("nothing", domain="data.example.com", limit=5)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
