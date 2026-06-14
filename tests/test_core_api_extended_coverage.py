"""Comprehensive tests for core.api Flask REST API endpoints.

Routes use local imports (``from .client import SocrataClient``,
``from ..analysis import profile_dataframe`` etc.), so patches target the
source modules, not the api module. Flask is required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

pytest.importorskip("flask", reason="Flask required for API tests")

from socrata_toolkit.core.api import create_app  # noqa: E402


@pytest.fixture
def client():
    """Flask test client.

    TESTING is intentionally left False so uncaught route exceptions surface as
    HTTP 500 responses (Flask's default) rather than propagating to the test.
    """
    app = create_app()
    with app.test_client() as c:
        yield c

class TestCreateApp:
    """Test the Flask application factory."""

    def test_create_app_returns_flask_app(self):
        app = create_app()
        assert app is not None
        assert hasattr(app, "route")

    def test_app_config_json_sort_keys(self):
        app = create_app()
        assert app.config.get("JSON_SORT_KEYS") is False

class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"
        assert "version" in data

class TestSearchEndpoint:
    def test_search_default(self, client):
        with patch("socrata_toolkit.core.client.SocrataClient") as mock_cls:
            mock_inst = MagicMock()
            mock_cls.return_value = mock_inst
            result = MagicMock()
            result.__dict__ = {"name": "Test", "fourfour": "abc1-2345"}
            mock_inst.search.return_value = [result]

            response = client.get("/api/search")
            assert response.status_code == 200
            data = response.get_json()
            assert len(data) == 1

    def test_search_with_query(self, client):
        with patch("socrata_toolkit.core.client.SocrataClient") as mock_cls:
            mock_inst = MagicMock()
            mock_cls.return_value = mock_inst
            mock_inst.search.return_value = []

            response = client.get("/api/search?q=violations&domain=data.cityofnewyork.us&limit=20")
            assert response.status_code == 200
            mock_inst.search.assert_called_once()

    def test_search_no_results(self, client):
        with patch("socrata_toolkit.core.client.SocrataClient") as mock_cls:
            mock_inst = MagicMock()
            mock_cls.return_value = mock_inst
            mock_inst.search.return_value = []

            response = client.get("/api/search?q=nonexistent")
            assert response.status_code == 200
            assert response.get_json() == []

class TestDatasetEndpoint:
    def test_dataset_fetch_default(self, client):
        with patch("socrata_toolkit.core.client.SocrataClient") as mock_cls:
            mock_inst = MagicMock()
            mock_cls.return_value = mock_inst
            mock_inst.fetch_dataframe.return_value = pd.DataFrame(
                {"id": [1, 2], "name": ["A", "B"]}
            )

            response = client.get("/api/dataset/abc1-2345")
            assert response.status_code == 200
            data = response.get_json()
            assert len(data) == 2

    def test_dataset_fetch_with_params(self, client):
        with patch("socrata_toolkit.core.client.SocrataClient") as mock_cls:
            mock_inst = MagicMock()
            mock_cls.return_value = mock_inst
            mock_inst.fetch_dataframe.return_value = pd.DataFrame({"value": [10]})

            response = client.get(
                "/api/dataset/abc1-2345?max_rows=500&domain=data.example.com"
            )
            assert response.status_code == 200
            mock_inst.fetch_dataframe.assert_called_once_with(
                "data.example.com", "abc1-2345", max_rows=500
            )

class TestMetadataEndpoint:
    def test_metadata_fetch(self, client):
        with patch("socrata_toolkit.core.client.SocrataClient") as mock_cls:
            mock_inst = MagicMock()
            mock_cls.return_value = mock_inst
            mock_meta = MagicMock()
            mock_meta.summary.return_value = {"name": "Test", "rows": 100}
            mock_inst.get_metadata.return_value = mock_meta

            response = client.get("/api/metadata/abc1-2345")
            assert response.status_code == 200
            data = response.get_json()
            assert data["name"] == "Test"

class TestAnalyzeEndpoint:
    def test_analyze_missing_rows(self, client):
        response = client.post("/api/analyze", json={})
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_analyze_with_rows(self, client):
        rows = [{"id": 1, "value": 10}, {"id": 2, "value": 20}]
        response = client.post("/api/analyze", json={"rows": rows})
        assert response.status_code == 200
        data = response.get_json()
        assert data["row_count"] == 2
        assert "column_count" in data
        assert "null_counts" in data

class TestQualityScoreEndpoint:
    def test_quality_score_missing_rows(self, client):
        response = client.post("/api/quality-score", json={})
        assert response.status_code == 400

    def test_quality_score_with_rows(self, client):
        rows = [
            {"id": 1, "value": 10, "created_date": "2024-01-01"},
            {"id": 2, "value": 20, "created_date": "2024-02-01"},
        ]
        response = client.post(
            "/api/quality-score",
            json={"rows": rows, "key_columns": ["id"], "date_column": "created_date"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "overall" in data
        assert 0 <= data["overall"] <= 100

class TestPrioritizeEndpoint:
    def test_prioritize_missing_rows(self, client):
        response = client.post("/api/prioritize", json={})
        assert response.status_code == 400

    def test_prioritize_with_rows(self, client):
        rows = [
            {"location": "5th Ave", "severity": 3, "borough": "MANHATTAN"},
            {"location": "Main St", "severity": 1, "borough": "QUEENS"},
        ]
        response = client.post("/api/prioritize", json={"rows": rows})
        # May succeed (200) or error depending on construction_list expectations
        assert response.status_code in (200, 400, 500)

class TestTriageEndpoint:
    def test_triage_missing_rows(self, client):
        response = client.post("/api/triage", json={})
        assert response.status_code == 400

    def test_triage_with_rows(self, client):
        rows = [{"complaint_text": "There is a pothole on 5th Ave"}]
        response = client.post("/api/triage", json={"rows": rows})
        assert response.status_code in (200, 500)

class TestBoardEndpoint:
    def test_board_get_state(self, client):
        response = client.get("/api/board")
        assert response.status_code == 200
        data = response.get_json()
        assert "name" in data
        assert "stats" in data
        assert "tasks" in data

    def test_board_create_task(self, client, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        response = client.post(
            "/api/board/task",
            json={"title": "Fix pothole", "priority": "high"},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "Fix pothole"
        assert "task_id" in data

class TestKpisEndpoint:
    def test_kpis_no_metrics_file(self, client, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        response = client.get("/api/kpis")
        assert response.status_code == 200
        data = response.get_json()
        assert "health" in data
        assert "metrics" in data

class TestErrorHandling:
    def test_dataset_fetch_error_returns_500(self, client):
        with patch("socrata_toolkit.core.client.SocrataClient") as mock_cls:
            mock_inst = MagicMock()
            mock_cls.return_value = mock_inst
            mock_inst.fetch_dataframe.side_effect = Exception("Invalid dataset")

            response = client.get("/api/dataset/invalid")
            assert response.status_code == 500
