"""Comprehensive tests for core.client module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from socrata_toolkit.core.client import SocrataClient, SocrataConfig
from socrata_toolkit.core.models import DatasetMetadata


class TestSocrataConfig:
    """Tests for SocrataConfig dataclass."""

    def test_default_config(self):
        config = SocrataConfig()
        assert config.app_token is None
        assert config.timeout == 30
        assert config.page_size == 1000

    def test_config_with_token(self):
        config = SocrataConfig(app_token="test_token")
        assert config.app_token == "test_token"
        assert config.timeout == 30

    def test_config_with_custom_values(self):
        config = SocrataConfig(
            app_token="token123",
            timeout=60,
            page_size=5000,
        )
        assert config.app_token == "token123"
        assert config.timeout == 60
        assert config.page_size == 5000


class TestSocrataClientInit:
    """Tests for SocrataClient initialization."""

    def test_client_with_default_config(self):
        client = SocrataClient()
        assert client.config is not None
        assert client.config.timeout == 30

    def test_client_with_custom_config(self):
        config = SocrataConfig(app_token="test", timeout=45)
        client = SocrataClient(config)
        assert client.config.app_token == "test"
        assert client.config.timeout == 45

    def test_client_headers_without_token(self):
        config = SocrataConfig(app_token=None)
        client = SocrataClient(config)
        headers = client._headers()
        # Without a token, no auth header is sent, but the client still
        # declares the JSON content type for the Socrata API.
        assert "X-App-Token" not in headers
        assert headers.get("Content-Type") == "application/json"

    def test_client_headers_with_token(self):
        config = SocrataConfig(app_token="my_token")
        client = SocrataClient(config)
        headers = client._headers()
        assert headers["X-App-Token"] == "my_token"


class TestSocrataClientWithEnv:
    """Tests for environment variable handling."""

    def test_client_with_env_token(self):
        with patch.dict("os.environ", {"SOCRATA_APP_TOKEN": "env_token"}):
            client = SocrataClient()
            headers = client._headers()
            assert headers["X-App-Token"] == "env_token"

    def test_client_config_timeout(self):
        config = SocrataConfig(timeout=5)
        client = SocrataClient(config)
        assert client.config.timeout == 5

    def test_client_config_page_size(self):
        config = SocrataConfig(page_size=500)
        client = SocrataClient(config)
        assert client.config.page_size == 500


class TestSocrataClientBuildSoql:
    """Tests for _build_soql helper method."""

    def test_build_soql_select_only(self):
        client = SocrataClient()
        query = client._build_soql(limit=1000, offset=0, select="id, name")
        assert "SELECT" in query
        assert "id, name" in query

    def test_build_soql_with_where(self):
        client = SocrataClient()
        query = client._build_soql(limit=1000, offset=0, select="id", where="id > 10")
        assert "WHERE" in query
        assert "id > 10" in query

    def test_build_soql_with_order(self):
        client = SocrataClient()
        query = client._build_soql(limit=1000, offset=0, select="id", order="id DESC")
        assert "ORDER BY" in query
        assert "id DESC" in query

    def test_build_soql_all_params(self):
        client = SocrataClient()
        query = client._build_soql(
            limit=50,
            offset=10,
            select="id, name",
            where="active = true",
            order="id DESC",
        )
        assert "SELECT" in query
        assert "id, name" in query
        assert "WHERE" in query
        assert "active = true" in query
        assert "ORDER BY" in query
        assert "LIMIT 50" in query
        assert "OFFSET 10" in query


class TestSocrataClientDataFrameConversion:
    """Tests for DataFrame conversion logic."""

    def test_fetch_dataframe_with_mocked_fetch(self):
        client = SocrataClient()
        with patch.object(client, "fetch_json") as mock_fetch:
            mock_fetch.return_value = iter(
                [
                    [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
                ]
            )

            df = client.fetch_dataframe("data.example.com", "dataset-id")
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 2
            assert "id" in df.columns
            assert "name" in df.columns

    def test_fetch_dataframe_empty_result(self):
        client = SocrataClient()
        with patch.object(client, "fetch_json") as mock_fetch:
            mock_fetch.return_value = iter([[]])

            df = client.fetch_dataframe("data.example.com", "empty-dataset")
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 0

    def test_fetch_dataframe_multiple_pages(self):
        client = SocrataClient()
        with patch.object(client, "fetch_json") as mock_fetch:
            mock_fetch.return_value = iter(
                [
                    [{"id": 1, "value": 10}, {"id": 2, "value": 20}],
                    [{"id": 3, "value": 30}],
                ]
            )

            df = client.fetch_dataframe("data.example.com", "dataset-id")
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 3


class TestSocrataClientSearch:
    """Tests for search method with proper mocking."""

    def test_search_with_query(self):
        client = SocrataClient()
        with patch("socrata_toolkit.core.client.with_retries") as mock_retries:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "results": [
                    {
                        "resource": {
                            "name": "Dataset 1",
                            "description": "Test dataset",
                            "id": "1234-abcd",
                        },
                        "metadata": {"domain": "data.example.com"},
                    }
                ],
                "count": 1,
            }
            mock_retries.return_value = mock_response

            results = client.search(query="violations")
            assert len(results) == 1
            assert results[0].name == "Dataset 1"

    def test_search_with_domain(self):
        client = SocrataClient()
        with patch("socrata_toolkit.core.client.with_retries") as mock_retries:
            mock_response = MagicMock()
            mock_response.json.return_value = {"results": [], "count": 0}
            mock_retries.return_value = mock_response

            results = client.search(domain="data.example.com")
            assert isinstance(results, list)
            assert len(results) == 0

    def test_search_with_category(self):
        client = SocrataClient()
        with patch("socrata_toolkit.core.client.with_retries") as mock_retries:
            mock_response = MagicMock()
            mock_response.json.return_value = {"results": [], "count": 0}
            mock_retries.return_value = mock_response

            results = client.search(category="Transportation")
            assert isinstance(results, list)

    def test_search_empty_results(self):
        client = SocrataClient()
        with patch("socrata_toolkit.core.client.with_retries") as mock_retries:
            mock_response = MagicMock()
            mock_response.json.return_value = {"results": []}
            mock_retries.return_value = mock_response

            results = client.search(query="nonexistent")
            assert len(results) == 0


class TestSocrataClientMetadata:
    """Tests for get_metadata method."""

    def test_get_metadata(self):
        client = SocrataClient()
        with patch("socrata_toolkit.core.client.with_retries") as mock_retries:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "name": "Test Dataset",
                "description": "A test dataset",
                "id": "test-id1",
                "columns": [
                    {"name": "id", "fieldName": "id", "dataTypeName": "number"},
                    {"name": "name", "fieldName": "name", "dataTypeName": "text"},
                ],
                "rowsUpdatedAt": 1700000000,
                "downloadCount": 100,
            }
            mock_retries.return_value = mock_response

            meta = client.get_metadata("data.example.com", "test-id1")
            assert isinstance(meta, DatasetMetadata)
            assert meta.name == "Test Dataset"

    def test_get_metadata_api_error(self):
        client = SocrataClient()
        with patch("socrata_toolkit.core.client.with_retries") as mock_retries:
            mock_retries.side_effect = RuntimeError("API error")
            with pytest.raises(RuntimeError):
                client.get_metadata("data.example.com", "invalid-id")
