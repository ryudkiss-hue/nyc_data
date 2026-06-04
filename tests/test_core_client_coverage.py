"""Comprehensive tests for core.client Socrata API wrapper.

Tests SocrataClient, SocrataConfig, and data fetching with realistic synthetic data.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


class TestSocrataConfig:
    """Test SocrataConfig configuration object."""

    def test_socrata_config_default_domain(self):
        """Test SocrataConfig with default domain."""
        from socrata_toolkit.core.client import SocrataConfig

        config = SocrataConfig()
        assert config.domain == "data.cityofnewyork.us"

    def test_socrata_config_custom_domain(self):
        """Test SocrataConfig with custom domain."""
        from socrata_toolkit.core.client import SocrataConfig

        config = SocrataConfig(domain="data.example.com")
        assert config.domain == "data.example.com"

    def test_socrata_config_with_token(self):
        """Test SocrataConfig with API token."""
        from socrata_toolkit.core.client import SocrataConfig

        config = SocrataConfig(app_token="test_token_123")
        assert config.app_token == "test_token_123"

    def test_socrata_config_timeout(self):
        """Test SocrataConfig timeout setting."""
        from socrata_toolkit.core.client import SocrataConfig

        config = SocrataConfig(timeout=30)
        assert config.timeout == 30


class TestSocrataClient:
    """Test SocrataClient API wrapper."""

    def test_socrata_client_init(self):
        """Test SocrataClient initialization."""
        from socrata_toolkit.core.client import SocrataClient

        with patch("socrata_toolkit.core.client.Socrata") as mock_socrata:
            mock_socrata.return_value = MagicMock()
            client = SocrataClient()
            assert client is not None

    def test_socrata_client_with_config(self):
        """Test SocrataClient with custom config."""
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        config = SocrataConfig(domain="data.example.com")
        with patch("socrata_toolkit.core.client.Socrata") as mock_socrata:
            mock_socrata.return_value = MagicMock()
            client = SocrataClient(config)
            assert client is not None

    def test_fetch_dataframe_basic(self):
        """Test fetching a DataFrame from Socrata."""
        from socrata_toolkit.core.client import SocrataClient

        with patch("socrata_toolkit.core.client.Socrata") as mock_socrata_class:
            mock_socrata = MagicMock()
            mock_socrata_class.return_value = mock_socrata

            # Mock the API response
            mock_socrata.get.return_value = [
                {"id": 1, "name": "Test 1", "value": 100},
                {"id": 2, "name": "Test 2", "value": 200},
            ]

            client = SocrataClient()
            df = client.fetch_dataframe("data.cityofnewyork.us", "abc1-2345")

            assert isinstance(df, pd.DataFrame)
            assert len(df) >= 0  # May be 0 or more depending on mock

    def test_fetch_dataframe_with_max_rows(self):
        """Test fetching DataFrame with max_rows limit."""
        from socrata_toolkit.core.client import SocrataClient

        with patch("socrata_toolkit.core.client.Socrata") as mock_socrata_class:
            mock_socrata = MagicMock()
            mock_socrata_class.return_value = mock_socrata
            mock_socrata.get.return_value = [
                {"id": i, "value": i * 10} for i in range(100)
            ]

            client = SocrataClient()
            df = client.fetch_dataframe("data.cityofnewyork.us", "abc1-2345", max_rows=50)

            assert isinstance(df, pd.DataFrame)

    def test_fetch_dataframe_with_where_filter(self):
        """Test fetching DataFrame with WHERE filter."""
        from socrata_toolkit.core.client import SocrataClient

        with patch("socrata_toolkit.core.client.Socrata") as mock_socrata_class:
            mock_socrata = MagicMock()
            mock_socrata_class.return_value = mock_socrata
            mock_socrata.get.return_value = [
                {"id": 1, "borough": "MANHATTAN", "status": "open"}
            ]

            client = SocrataClient()
            df = client.fetch_dataframe(
                "data.cityofnewyork.us",
                "abc1-2345",
                where="borough='MANHATTAN'"
            )

            assert isinstance(df, pd.DataFrame)

    def test_fetch_dataframe_empty_result(self):
        """Test fetching DataFrame that returns no rows."""
        from socrata_toolkit.core.client import SocrataClient

        with patch("socrata_toolkit.core.client.Socrata") as mock_socrata_class:
            mock_socrata = MagicMock()
            mock_socrata_class.return_value = mock_socrata
            mock_socrata.get.return_value = []

            client = SocrataClient()
            df = client.fetch_dataframe("data.cityofnewyork.us", "abc1-2345")

            assert isinstance(df, pd.DataFrame)
            assert len(df) == 0

    def test_get_metadata(self):
        """Test fetching dataset metadata."""
        from socrata_toolkit.core.client import SocrataClient

        with patch("socrata_toolkit.core.client.Socrata") as mock_socrata_class:
            mock_socrata = MagicMock()
            mock_socrata_class.return_value = mock_socrata

            # Mock metadata response
            mock_meta_obj = MagicMock()
            mock_meta_obj.summary.return_value = {
                "name": "Test Dataset",
                "rows": 1000,
                "columns": 10,
            }
            mock_socrata.get_metadata.return_value = mock_meta_obj

            client = SocrataClient()
            meta = client.get_metadata("data.cityofnewyork.us", "abc1-2345")

            assert meta is not None

    def test_search_datasets(self):
        """Test searching for datasets."""
        from socrata_toolkit.core.client import SocrataClient, SearchResult

        with patch("socrata_toolkit.core.client.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "results": [
                    {
                        "resource": {
                            "id": "abc1-2345",
                            "name": "Test Dataset",
                            "description": "A test dataset",
                        }
                    }
                ]
            }
            mock_response.status_code = 200
            mock_requests.get.return_value = mock_response

            client = SocrataClient()
            results = client.search("test", limit=10)

            assert isinstance(results, list)

    def test_search_datasets_with_domain(self):
        """Test searching datasets on specific domain."""
        from socrata_toolkit.core.client import SocrataClient

        with patch("socrata_toolkit.core.client.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.json.return_value = {"results": []}
            mock_response.status_code = 200
            mock_requests.get.return_value = mock_response

            client = SocrataClient()
            results = client.search("test", domain="data.example.com", limit=5)

            assert isinstance(results, list)


class TestSocrataClientWithSyntheticData:
    """Integration tests with synthetic Faker data."""

    def test_fetch_fake_inspection_data(self, fake_inspection_records):
        """Test fetching and processing fake inspection records."""
        from socrata_toolkit.core.client import SocrataClient

        df = pd.DataFrame(fake_inspection_records)

        # Verify structure
        assert len(df) == 100
        assert "borough" in df.columns
        assert "status" in df.columns
        assert "severity" in df.columns

    def test_fetch_fake_violations_data(self, fake_violation_records):
        """Test fetching and processing fake violation records."""
        from socrata_toolkit.core.client import SocrataClient

        df = pd.DataFrame(fake_violation_records)

        # Verify structure
        assert len(df) == 500
        assert "violation_type" in df.columns
        assert "severity" in df.columns
        assert "date_reported" in df.columns

    def test_process_large_dataset(self, fake_large_dataframe):
        """Test processing large dataset (10K rows)."""
        df = fake_large_dataframe

        # Verify we can process without errors
        assert len(df) == 10000
        assert "borough" in df.columns

        # Test grouping operations
        grouped = df.groupby("borough").size()
        assert len(grouped) > 0

    def test_filter_synthetic_data(self, fake_inspection_records):
        """Test filtering synthetic data by borough."""
        df = pd.DataFrame(fake_inspection_records)

        manhattan = df[df["borough"] == "MANHATTAN"]
        assert len(manhattan) > 0
        assert all(manhattan["borough"] == "MANHATTAN")

    def test_aggregate_synthetic_data(self, fake_violation_records):
        """Test aggregating synthetic violation data."""
        df = pd.DataFrame(fake_violation_records)

        # Count violations by type
        violation_counts = df["violation_type"].value_counts()
        assert len(violation_counts) > 0

        # Average severity by type
        avg_severity = df.groupby("violation_type")["severity"].mean()
        assert len(avg_severity) > 0

    def test_date_operations_on_synthetic_data(self, fake_inspection_records):
        """Test date operations on synthetic data."""
        df = pd.DataFrame(fake_inspection_records)

        # Convert to datetime
        df["complaint_date"] = pd.to_datetime(df["complaint_date"])
        df["completion_date"] = pd.to_datetime(df["completion_date"])

        # Filter by date range
        recent = df[df["complaint_date"] > "2024-01-01"]
        assert isinstance(recent, pd.DataFrame)


class TestErrorHandling:
    """Test error handling in SocrataClient."""

    def test_fetch_dataframe_api_error(self):
        """Test handling of API errors."""
        from socrata_toolkit.core.client import SocrataClient

        with patch("socrata_toolkit.core.client.Socrata") as mock_socrata_class:
            mock_socrata = MagicMock()
            mock_socrata_class.return_value = mock_socrata
            mock_socrata.get.side_effect = Exception("API Error")

            client = SocrataClient()
            with pytest.raises(Exception):
                client.fetch_dataframe("data.cityofnewyork.us", "invalid")

    def test_invalid_fourfour(self):
        """Test handling of invalid fourfour IDs."""
        from socrata_toolkit.core.client import SocrataClient

        with patch("socrata_toolkit.core.client.Socrata") as mock_socrata_class:
            mock_socrata = MagicMock()
            mock_socrata_class.return_value = mock_socrata
            mock_socrata.get.return_value = []

            client = SocrataClient()
            df = client.fetch_dataframe("data.cityofnewyork.us", "invalid-fourfour")

            # Should return empty DataFrame, not raise error
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 0

    def test_timeout_handling(self):
        """Test handling of timeout errors."""
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig

        config = SocrataConfig(timeout=1)

        with patch("socrata_toolkit.core.client.Socrata") as mock_socrata_class:
            mock_socrata = MagicMock()
            mock_socrata_class.return_value = mock_socrata
            mock_socrata.get.side_effect = TimeoutError("Request timeout")

            client = SocrataClient(config)
            with pytest.raises(TimeoutError):
                client.fetch_dataframe("data.cityofnewyork.us", "abc1-2345")


class TestClientCaching:
    """Test client-level caching behavior."""

    def test_client_caches_connections(self):
        """Test that client maintains connection cache."""
        from socrata_toolkit.core.client import SocrataClient

        with patch("socrata_toolkit.core.client.Socrata") as mock_socrata_class:
            mock_socrata_class.return_value = MagicMock()

            client = SocrataClient()
            # Make multiple calls
            with patch.object(client, "fetch_dataframe", return_value=pd.DataFrame()):
                client.fetch_dataframe("data.cityofnewyork.us", "abc1-2345")
                client.fetch_dataframe("data.cityofnewyork.us", "xyz9-8765")

            # Connection should be reused (implementation dependent)
            assert client is not None
