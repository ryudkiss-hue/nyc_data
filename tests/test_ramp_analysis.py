"""Tests for ramp_analysis module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from socrata_toolkit.analyst.ramp_analysis import fetch_ramp_full_corpus


class TestFetchRampFullCorpus:
    """Tests for fetch_ramp_full_corpus function."""

    def test_import_ok(self):
        """Test that the function can be imported."""
        assert callable(fetch_ramp_full_corpus)

    def test_raises_on_missing_token(self):
        """Test that ValueError is raised when no token is provided."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="No API token provided"):
                fetch_ramp_full_corpus()

    def test_returns_dataframe(self):
        """Test that function returns a pandas DataFrame."""
        mock_batch_1 = [
            {
                "corner_id": "C001",
                "borough": "Manhattan",
                "total_complaints": 5,
                "resolved_complaints": 3,
                "in_progress_complaints": 2,
            },
            {
                "corner_id": "C002",
                "borough": "Brooklyn",
                "total_complaints": 3,
                "resolved_complaints": 2,
                "in_progress_complaints": 1,
            },
        ]
        mock_batch_2 = [
            {
                "corner_id": "C003",
                "borough": "Queens",
                "total_complaints": 7,
                "resolved_complaints": 5,
                "in_progress_complaints": 2,
            },
        ]

        with patch("socrata_toolkit.analyst.ramp_analysis.SocrataClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.fetch_json.return_value = iter([mock_batch_1, mock_batch_2])

            result = fetch_ramp_full_corpus(api_token="test_token")

            assert isinstance(result, pd.DataFrame)
            assert len(result) == 3
            expected_cols = {
                "corner_id",
                "borough",
                "total_complaints",
                "resolved_complaints",
                "in_progress_complaints",
            }
            assert set(result.columns) == expected_cols

    def test_pagination_with_multiple_batches(self):
        """Test that multiple batches are correctly aggregated."""
        batches = [
            [{"corner_id": f"C{i}", "borough": "Test"} for i in range(50000)],
            [{"corner_id": f"C{50000 + i}", "borough": "Test"} for i in range(25000)],
        ]

        with patch("socrata_toolkit.analyst.ramp_analysis.SocrataClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.fetch_json.return_value = iter(batches)

            result = fetch_ramp_full_corpus(api_token="test_token")

            assert len(result) == 75000

    def test_uses_provided_token(self):
        """Test that provided token is used."""
        with patch("socrata_toolkit.analyst.ramp_analysis.SocrataClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.fetch_json.return_value = iter([[]])

            fetch_ramp_full_corpus(api_token="custom_token")

            # Check that SocrataConfig was created with the custom token
            call_args = mock_client_cls.call_args
            assert call_args is not None
            config = call_args[0][0]
            assert config.app_token == "custom_token"

    def test_uses_env_token_when_not_provided(self):
        """Test that environment token is used when not provided as argument."""
        with patch.dict("os.environ", {"SOCRATA_APP_TOKEN": "env_token"}):
            with patch("socrata_toolkit.analyst.ramp_analysis.SocrataClient") as mock_client_cls:
                mock_client = MagicMock()
                mock_client_cls.return_value = mock_client
                mock_client.fetch_json.return_value = iter([[]])

                fetch_ramp_full_corpus()

                # Check that SocrataConfig was created with the env token
                call_args = mock_client_cls.call_args
                assert call_args is not None
                config = call_args[0][0]
                assert config.app_token == "env_token"

    def test_calls_fetch_json_with_correct_params(self):
        """Test that fetch_json is called with correct dataset parameters."""
        with patch("socrata_toolkit.analyst.ramp_analysis.SocrataClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.fetch_json.return_value = iter([[]])

            fetch_ramp_full_corpus(api_token="test_token")

            # Verify fetch_json was called with correct parameters
            mock_client.fetch_json.assert_called_once_with(
                domain="data.cityofnewyork.us",
                fourfour="e7gc-ub6z",
            )

    def test_handles_empty_response(self):
        """Test handling of empty API response."""
        with patch("socrata_toolkit.analyst.ramp_analysis.SocrataClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.fetch_json.return_value = iter([])

            result = fetch_ramp_full_corpus(api_token="test_token")

            assert isinstance(result, pd.DataFrame)
            assert len(result) == 0

    def test_filters_expected_columns(self):
        """Test that only expected columns are returned."""
        batch = [
            {
                "corner_id": "C001",
                "borough": "Manhattan",
                "total_complaints": 5,
                "resolved_complaints": 3,
                "in_progress_complaints": 2,
                "extra_column": "should_be_removed",
            },
        ]

        with patch("socrata_toolkit.analyst.ramp_analysis.SocrataClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.fetch_json.return_value = iter([batch])

            result = fetch_ramp_full_corpus(api_token="test_token")

            # Should only have expected columns
            assert "extra_column" not in result.columns
            assert "corner_id" in result.columns
            assert "borough" in result.columns

    def test_respects_page_size_in_config(self):
        """Test that page_size is set to 50000 in SocrataConfig."""
        with patch("socrata_toolkit.analyst.ramp_analysis.SocrataClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.fetch_json.return_value = iter([[]])

            fetch_ramp_full_corpus(api_token="test_token")

            # Check that SocrataConfig was created with page_size=50000
            call_args = mock_client_cls.call_args
            assert call_args is not None
            config = call_args[0][0]
            assert config.page_size == 50000
