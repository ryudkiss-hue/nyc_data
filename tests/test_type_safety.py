"""
Tests for type safety in Socrata ingestion parameters.
Ensures max_rows and page_size handle string inputs correctly.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from socrata_toolkit.core.client import SocrataClient, SocrataConfig


def _mock_resp(json_payload):
    resp = MagicMock()
    resp.json.return_value = json_payload
    resp.status_code = 200
    return resp

class TestIngestionTypeSafety:
    @patch("socrata_toolkit.core.client.requests.post")
    def test_fetch_json_soda3_string_max_rows(self, mock_post):
        """SODA3 POST path should cast string max_rows to int."""
        client = SocrataClient(SocrataConfig(app_token="fake", page_size=1000))
        mock_post.side_effect = [_mock_resp([{"id": 1}]), _mock_resp([])]

        # This would fail with TypeError: '<' not supported between 'str' and 'int'
        # if max_rows was not cast before min(page_size, remaining)
        batches = list(client.fetch_json("data.city", "abcd-1234", max_rows="500"))
        assert len(batches) == 1

    @patch("socrata_toolkit.core.client.requests.get")
    def test_fetch_json_soda2_string_max_rows(self, mock_get):
        """SODA2 GET path should cast string max_rows to int."""
        client = SocrataClient(SocrataConfig(app_token=None, page_size=1000))
        mock_get.side_effect = [_mock_resp([{"id": 1}]), _mock_resp([])]

        with pytest.warns(UserWarning):
            batches = list(client.fetch_json("data.city", "abcd-1234", max_rows="500"))
        assert len(batches) == 1

    @patch("socrata_toolkit.core.client.requests.post")
    def test_fetch_geojson_soda3_string_max_rows(self, mock_post):
        """fetch_geojson SODA3 path should cast string max_rows to int."""
        client = SocrataClient(SocrataConfig(app_token="fake", page_size=1000))
        # Need to return an empty batch to break the loop or mock the countdown
        mock_post.side_effect = [_mock_resp({"features": [{"id": 1}]}), _mock_resp({"features": []})]

        fc = client.fetch_geojson("data.city", "abcd-1234", max_rows="500")
        assert len(fc["features"]) == 1
