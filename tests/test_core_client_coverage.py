"""Comprehensive tests for core.client Socrata API wrapper.

Tests SocrataClient and SocrataConfig. The client uses `requests` directly
(SODA3 POST with token, SODA2 GET fallback without) wrapped in `with_retries`,
so tests patch `socrata_toolkit.core.client.requests`.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


def _mock_response(json_value):
    """Build a mock requests.Response whose .json() returns json_value."""
    resp = MagicMock()
    resp.json.return_value = json_value
    resp.status_code = 200
    return resp


def _paged_get(pages):
    """Return a side_effect callable yielding successive pages then []."""
    sequence = [_mock_response(p) for p in pages] + [_mock_response([])]
    it = iter(sequence)

    def _call(*args, **kwargs):
        return next(it)

    return _call


class TestSocrataConfig:
    """Test SocrataConfig configuration dataclass."""

    def test_default_app_token_none(self):
        from socrata_toolkit.core.client import SocrataConfig

        config = SocrataConfig()
        assert config.app_token is None

    def test_default_timeout(self):
        from socrata_toolkit.core.client import SocrataConfig

        config = SocrataConfig()
        assert config.timeout == 30

    def test_default_page_size(self):
        from socrata_toolkit.core.client import SocrataConfig

        config = SocrataConfig()
        assert config.page_size == 1000

    def test_with_token(self):
        from socrata_toolkit.core.client import SocrataConfig

        config = SocrataConfig(app_token="test_token_123")
        assert config.app_token == "test_token_123"

    def test_custom_timeout(self):
        from socrata_toolkit.core.client import SocrataConfig

        config = SocrataConfig(timeout=60)
        assert config.timeout == 60

    def test_custom_page_size(self):
        from socrata_toolkit.core.client import SocrataConfig

        config = SocrataConfig(page_size=500)
        assert config.page_size == 500


class TestSocrataClientInit:
    """Test SocrataClient initialization."""

    def test_init_default_config(self, monkeypatch):
        from socrata_toolkit.core.client import SocrataClient

        monkeypatch.delenv("SOCRATA_APP_TOKEN", raising=False)
        client = SocrataClient()
        assert client.config is not None

    def test_init_reads_env_token(self, monkeypatch):
        from socrata_toolkit.core.client import SocrataClient

        monkeypatch.setenv("SOCRATA_APP_TOKEN", "env_token_xyz")
        client = SocrataClient()
        assert client.config.app_token == "env_token_xyz"

    def test_init_with_explicit_config(self):
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        config = SocrataConfig(app_token="explicit")
        client = SocrataClient(config)
        assert client.config.app_token == "explicit"

    def test_headers_with_token(self):
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig(app_token="tok"))
        headers = client._headers()
        assert headers["X-App-Token"] == "tok"

    def test_headers_without_token(self):
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig(app_token=None))
        headers = client._headers()
        assert "X-App-Token" not in headers


class TestBuildSoql:
    """Test the _build_soql query builder."""

    def test_basic_select_all(self):
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig())
        soql = client._build_soql(limit=10, offset=0)
        assert "SELECT *" in soql
        assert "LIMIT 10" in soql
        assert "OFFSET 0" in soql

    def test_with_select(self):
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig())
        soql = client._build_soql(limit=10, offset=0, select="borough, count(*)")
        assert "SELECT borough, count(*)" in soql

    def test_with_where(self):
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig())
        soql = client._build_soql(limit=10, offset=0, where="borough='MANHATTAN'")
        assert "WHERE borough='MANHATTAN'" in soql

    def test_with_order(self):
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig())
        soql = client._build_soql(limit=10, offset=0, order="created_date DESC")
        assert "ORDER BY created_date DESC" in soql

    def test_full_query(self):
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig())
        soql = client._build_soql(
            limit=50, offset=100, select="a, b", where="x>1", order="a"
        )
        assert "SELECT a, b" in soql
        assert "WHERE x>1" in soql
        assert "ORDER BY a" in soql
        assert "LIMIT 50" in soql
        assert "OFFSET 100" in soql


class TestFetchDataframe:
    """Test fetch_dataframe via SODA2/SODA3 paths."""

    def test_fetch_soda2_without_token(self):
        """Without a token, falls back to SODA2 GET."""
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig(app_token=None))
        page = [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]
        with patch("socrata_toolkit.core.client.requests") as mock_requests:
            mock_requests.get.side_effect = _paged_get([page])
            with pytest.warns(UserWarning):
                df = client.fetch_dataframe("data.cityofnewyork.us", "abc1-2345")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ["id", "name"]

    def test_fetch_soda3_with_token(self):
        """With a token, uses SODA3 POST endpoint."""
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig(app_token="tok"))
        page = [{"id": "1", "value": 10}]
        with patch("socrata_toolkit.core.client.requests") as mock_requests:
            mock_requests.post.side_effect = _paged_get([page])
            df = client.fetch_dataframe("data.cityofnewyork.us", "abc1-2345")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        mock_requests.post.assert_called()

    def test_fetch_empty_result(self):
        """Empty dataset returns empty DataFrame."""
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig(app_token="tok"))
        with patch("socrata_toolkit.core.client.requests") as mock_requests:
            mock_requests.post.side_effect = _paged_get([])
            df = client.fetch_dataframe("data.cityofnewyork.us", "abc1-2345")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_fetch_with_max_rows(self):
        """max_rows limits the number of returned rows."""
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig(app_token="tok", page_size=2))
        page = [{"id": str(i)} for i in range(2)]
        with patch("socrata_toolkit.core.client.requests") as mock_requests:
            mock_requests.post.side_effect = _paged_get([page])
            df = client.fetch_dataframe("data.cityofnewyork.us", "abc1-2345", max_rows=2)

        assert len(df) == 2

    def test_fetch_with_where(self):
        """WHERE filter is passed through to the SoQL query."""
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig(app_token="tok"))
        page = [{"id": "1", "borough": "MANHATTAN"}]
        with patch("socrata_toolkit.core.client.requests") as mock_requests:
            mock_requests.post.side_effect = _paged_get([page])
            df = client.fetch_dataframe(
                "data.cityofnewyork.us", "abc1-2345", where="borough='MANHATTAN'"
            )

        assert len(df) == 1
        # Verify the WHERE clause made it into the POSTed query
        call_kwargs = mock_requests.post.call_args
        posted_query = call_kwargs.kwargs["json"]["query"]
        assert "WHERE borough='MANHATTAN'" in posted_query


class TestSearch:
    """Test dataset search."""

    def test_search_returns_results(self):
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig())
        payload = {
            "results": [
                {
                    "resource": {
                        "id": "abc1-2345",
                        "name": "Test Dataset",
                        "description": "desc",
                        "tags": ["a"],
                    },
                    "metadata": {"domain": "data.cityofnewyork.us"},
                }
            ]
        }
        with patch("socrata_toolkit.core.client.requests") as mock_requests:
            mock_requests.get.return_value = _mock_response(payload)
            results = client.search("test", limit=10)

        assert len(results) == 1
        assert results[0].name == "Test Dataset"
        assert results[0].fourfour == "abc1-2345"

    def test_search_empty_results(self):
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig())
        with patch("socrata_toolkit.core.client.requests") as mock_requests:
            mock_requests.get.return_value = _mock_response({"results": []})
            results = client.search("nonexistent")

        assert results == []

    def test_search_with_domain_and_category(self):
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig())
        with patch("socrata_toolkit.core.client.requests") as mock_requests:
            mock_requests.get.return_value = _mock_response({"results": []})
            client.search("q", domain="data.example.com", category="Transportation")
            params = mock_requests.get.call_args.kwargs["params"]
            assert params["domains"] == "data.example.com"
            assert params["categories"] == "Transportation"


class TestGetMetadata:
    """Test get_metadata."""

    def test_metadata_basic(self):
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig())
        payload = {
            "name": "Test Dataset",
            "description": "A description",
            "rowsCount": 1000,
            "columns": [{"name": "id"}],
        }
        with patch("socrata_toolkit.core.client.requests") as mock_requests:
            mock_requests.get.return_value = _mock_response(payload)
            meta = client.get_metadata("data.cityofnewyork.us", "abc1-2345")

        assert meta.name == "Test Dataset"
        assert meta.row_count == 1000
        assert meta.fourfour == "abc1-2345"

    def test_metadata_with_license(self):
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig())
        payload = {
            "name": "X",
            "license": {"name": "CC0"},
            "columns": [],
        }
        with patch("socrata_toolkit.core.client.requests") as mock_requests:
            mock_requests.get.return_value = _mock_response(payload)
            meta = client.get_metadata("data.cityofnewyork.us", "abc1-2345")

        assert meta.license == "CC0"


class TestFetchGeojson:
    """Test fetch_geojson SODA3 (token) and SODA2 (no token) paths."""

    def test_fetch_geojson_soda3_with_token(self):
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig(app_token="tok"))
        fc_page = {"type": "FeatureCollection", "features": [{"type": "Feature", "id": 1}]}
        with patch("socrata_toolkit.core.client.requests") as mock_requests:
            mock_requests.post.side_effect = [
                _mock_response(fc_page),
                _mock_response({"features": []}),
            ]
            fc = client.fetch_geojson("data.cityofnewyork.us", "abc1-2345")

        assert fc["type"] == "FeatureCollection"
        assert len(fc["features"]) == 1
        mock_requests.post.assert_called()

    def test_fetch_geojson_soda2_without_token(self):
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig(app_token=None))
        fc_page = {"type": "FeatureCollection", "features": [{"type": "Feature", "id": 9}]}
        with patch("socrata_toolkit.core.client.requests") as mock_requests:
            mock_requests.get.side_effect = [
                _mock_response(fc_page),
                _mock_response({"features": []}),
            ]
            with pytest.warns(UserWarning):
                fc = client.fetch_geojson("data.cityofnewyork.us", "abc1-2345")

        assert len(fc["features"]) == 1
        mock_requests.get.assert_called()

    def test_fetch_geojson_empty(self):
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig(app_token="tok"))
        with patch("socrata_toolkit.core.client.requests") as mock_requests:
            mock_requests.post.return_value = _mock_response({"features": []})
            fc = client.fetch_geojson("data.cityofnewyork.us", "abc1-2345")

        assert fc["features"] == []

    def test_fetch_geojson_with_max_rows(self):
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig(app_token="tok", page_size=1))
        fc_page = {"features": [{"type": "Feature", "id": 1}]}
        with patch("socrata_toolkit.core.client.requests") as mock_requests:
            mock_requests.post.return_value = _mock_response(fc_page)
            fc = client.fetch_geojson("data.cityofnewyork.us", "abc1-2345", max_rows=1)

        assert len(fc["features"]) == 1


class TestFetchSince:
    """Test fetch_since delta fetch."""

    def test_fetch_since_builds_where(self):
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig(app_token="tok"))
        page = [{"id": "1"}]
        with patch("socrata_toolkit.core.client.requests") as mock_requests:
            mock_requests.post.side_effect = _paged_get([page])
            batches = list(
                client.fetch_since(
                    "data.cityofnewyork.us", "abc1-2345", "updated_at", "2024-01-01T00:00:00"
                )
            )

        assert len(batches) == 1
        posted_query = mock_requests.post.call_args.kwargs["json"]["query"]
        assert "updated_at > '2024-01-01T00:00:00'" in posted_query

    def test_fetch_since_combines_with_existing_where(self):
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        client = SocrataClient(SocrataConfig(app_token="tok"))
        page = [{"id": "1"}]
        with patch("socrata_toolkit.core.client.requests") as mock_requests:
            mock_requests.post.side_effect = _paged_get([page])
            list(
                client.fetch_since(
                    "data.cityofnewyork.us",
                    "abc1-2345",
                    "updated_at",
                    "2024-01-01",
                    where="borough='MN'",
                )
            )

        posted_query = mock_requests.post.call_args.kwargs["json"]["query"]
        assert "borough='MN'" in posted_query
        assert "updated_at > '2024-01-01'" in posted_query


class TestSyntheticDataProcessing:
    """Validate downstream processing of synthetic Faker data."""

    def test_process_fake_inspection_records(self, fake_inspection_records):
        df = pd.DataFrame(fake_inspection_records)
        assert len(df) == 100
        assert {"borough", "status", "severity"}.issubset(df.columns)

    def test_filter_by_borough(self, fake_inspection_records):
        df = pd.DataFrame(fake_inspection_records)
        manhattan = df[df["borough"] == "MANHATTAN"]
        assert all(manhattan["borough"] == "MANHATTAN")

    def test_aggregate_violations(self, fake_violation_records):
        df = pd.DataFrame(fake_violation_records)
        counts = df["violation_type"].value_counts()
        assert counts.sum() == 500

    def test_large_dataset_grouping(self, fake_large_dataframe):
        grouped = fake_large_dataframe.groupby("borough").size()
        assert grouped.sum() == 10000


class TestErrorHandling:
    """Test error propagation."""

    def test_fetch_api_error_propagates(self):
        """Underlying request errors surface as SocrataToolkitError after retries."""
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig
        from socrata_toolkit.core.utils import SocrataToolkitError

        client = SocrataClient(SocrataConfig(app_token="tok"))
        with patch("socrata_toolkit.core.client.requests") as mock_requests:
            mock_requests.post.side_effect = RuntimeError("API Error")
            with pytest.raises(SocrataToolkitError):
                client.fetch_dataframe("data.cityofnewyork.us", "invalid")
