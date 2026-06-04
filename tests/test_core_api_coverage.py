"""Tests for socrata_toolkit.core.api — Flask application factory and endpoints."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Guard: skip the whole module if Flask is not installed
# ---------------------------------------------------------------------------

flask = pytest.importorskip("flask", reason="flask not installed")


from socrata_toolkit.core.api import create_app  # noqa: E402 — must come after guard


@pytest.fixture()
def client():
    """Create a Flask test client from the application factory."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# /api/health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    """Tests for GET /api/health."""

    def test_health_returns_200(self, client):
        """Health endpoint returns HTTP 200."""
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_returns_ok_status(self, client):
        """Health endpoint body contains status: ok."""
        resp = client.get("/api/health")
        data = resp.get_json()
        assert data["status"] == "ok"

    def test_health_returns_version(self, client):
        """Health endpoint body contains a version string."""
        resp = client.get("/api/health")
        data = resp.get_json()
        assert "version" in data


# ---------------------------------------------------------------------------
# /api/search
# ---------------------------------------------------------------------------

class TestSearchEndpoint:
    """Tests for GET /api/search."""

    def test_search_returns_200(self, client):
        """Search endpoint returns HTTP 200 when client succeeds."""
        mock_result = MagicMock()
        mock_result.__dict__ = {"name": "Test Dataset", "fourfour": "abcd-1234"}

        with patch("socrata_toolkit.core.api.create_app.<locals>.search") as mock_fn:
            # Instead, patch SocrataClient directly
            pass

        with patch("socrata_toolkit.core.client.SocrataClient.search", return_value=[]):
            resp = client.get("/api/search?q=violations")
        assert resp.status_code == 200

    def test_search_returns_list(self, client):
        """Search endpoint returns a JSON list."""
        with patch("socrata_toolkit.core.client.SocrataClient.search", return_value=[]):
            resp = client.get("/api/search?q=test")
        assert isinstance(resp.get_json(), list)

    def test_search_default_query(self, client):
        """Search endpoint works with empty query parameter."""
        with patch("socrata_toolkit.core.client.SocrataClient.search", return_value=[]):
            resp = client.get("/api/search")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /api/analyze  (POST)
# ---------------------------------------------------------------------------

class TestAnalyzeEndpoint:
    """Tests for POST /api/analyze."""

    def test_analyze_missing_rows_returns_400(self, client):
        """Payload without 'rows' key returns HTTP 400."""
        resp = client.post(
            "/api/analyze",
            json={"not_rows": []},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_analyze_empty_body_returns_400(self, client):
        """Empty body returns HTTP 400."""
        resp = client.post("/api/analyze", data="{}", content_type="application/json")
        assert resp.status_code == 400

    def test_analyze_valid_rows_returns_200(self, client):
        """Valid rows payload returns HTTP 200 with expected keys."""
        payload = {
            "rows": [
                {"borough": "MANHATTAN", "count": 5},
                {"borough": "BRONX", "count": 3},
            ]
        }
        resp = client.post("/api/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "row_count" in data
        assert "column_count" in data

    def test_analyze_returns_row_count(self, client):
        """row_count in response matches the number of supplied rows."""
        payload = {"rows": [{"a": 1}, {"a": 2}, {"a": 3}]}
        resp = client.post("/api/analyze", json=payload)
        data = resp.get_json()
        assert data["row_count"] == 3


# ---------------------------------------------------------------------------
# /api/quality-score  (POST)
# ---------------------------------------------------------------------------

class TestQualityScoreEndpoint:
    """Tests for POST /api/quality-score."""

    def test_quality_score_missing_rows_returns_400(self, client):
        """Payload without 'rows' key returns HTTP 400."""
        resp = client.post(
            "/api/quality-score",
            json={"key_columns": ["id"]},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_quality_score_valid_payload_returns_200(self, client):
        """Valid rows payload returns HTTP 200 with score fields."""
        payload = {
            "rows": [
                {"id": "1", "borough": "MANHATTAN", "created_date": "2025-01-01"},
                {"id": "2", "borough": "BRONX", "created_date": "2025-01-02"},
            ],
            "key_columns": ["id"],
            "date_column": "created_date",
        }
        resp = client.post("/api/quality-score", json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "overall" in data
        assert "completeness" in data

    def test_quality_score_returns_numeric_overall(self, client):
        """'overall' field is a number between 0 and 100."""
        payload = {"rows": [{"a": 1, "b": 2}]}
        resp = client.post("/api/quality-score", json=payload)
        data = resp.get_json()
        assert 0 <= data["overall"] <= 100


# ---------------------------------------------------------------------------
# /api/prioritize  (POST)
# ---------------------------------------------------------------------------

class TestPrioritizeEndpoint:
    """Tests for POST /api/prioritize."""

    def test_prioritize_missing_rows_returns_400(self, client):
        """Payload without 'rows' key returns HTTP 400."""
        resp = client.post("/api/prioritize", json={}, content_type="application/json")
        assert resp.status_code == 400

    def test_prioritize_valid_rows_returns_200(self, client):
        """Valid rows payload returns HTTP 200 with summary and rows."""
        payload = {
            "rows": [
                {
                    "defect_grade": "A",
                    "location_type": "Sidewalk",
                    "block_or_lot": "100",
                    "description": "Cracked sidewalk flag near curb ramp",
                },
            ]
        }
        resp = client.post("/api/prioritize", json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "summary" in data
        assert "rows" in data


# ---------------------------------------------------------------------------
# /api/board  (GET)
# ---------------------------------------------------------------------------

class TestBoardEndpoint:
    """Tests for GET /api/board."""

    def test_board_returns_200(self, client):
        """Board endpoint returns HTTP 200."""
        with patch("pathlib.Path.exists", return_value=False):
            resp = client.get("/api/board")
        assert resp.status_code == 200

    def test_board_has_expected_keys(self, client):
        """Board response contains name, stats and tasks keys."""
        with patch("pathlib.Path.exists", return_value=False):
            resp = client.get("/api/board")
        data = resp.get_json()
        assert "name" in data
        assert "stats" in data
        assert "tasks" in data


# ---------------------------------------------------------------------------
# /api/kpis  (GET)
# ---------------------------------------------------------------------------

class TestKPIsEndpoint:
    """Tests for GET /api/kpis."""

    def test_kpis_no_metrics_file_returns_unknown(self, client):
        """When no metrics file exists, health is 'unknown'."""
        with patch("pathlib.Path.exists", return_value=False):
            resp = client.get("/api/kpis")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["health"] == "unknown"
        assert data["metrics"] == []


# ---------------------------------------------------------------------------
# create_app factory
# ---------------------------------------------------------------------------

class TestCreateApp:
    """Tests for create_app function."""

    def test_create_app_returns_flask_app(self):
        """create_app returns an object with the Flask test_client interface."""
        app = create_app()
        assert hasattr(app, "test_client")

    def test_multiple_create_app_calls_independent(self):
        """Each call to create_app returns a fresh application instance."""
        app1 = create_app()
        app2 = create_app()
        assert app1 is not app2
