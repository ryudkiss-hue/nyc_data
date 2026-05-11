import json
import pytest

try:
    from flask import Flask
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


@pytest.mark.skipif(not HAS_FLASK, reason="flask not installed")
class TestFlaskAPI:
    @pytest.fixture
    def client(self):
        from socrata_toolkit.core.api import create_app
        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"

    def test_analyze_endpoint(self, client):
        payload = {
            "rows": [
                {"id": 1, "name": "a", "val": 10},
                {"id": 2, "name": "b", "val": None},
            ]
        }
        resp = client.post("/api/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["row_count"] == 2

    def test_analyze_bad_request(self, client):
        resp = client.post("/api/analyze", json={})
        assert resp.status_code == 400

    def test_quality_score_endpoint(self, client):
        payload = {
            "rows": [
                {"id": 1, "name": "a"},
                {"id": 2, "name": "b"},
            ],
            "key_columns": ["id"],
        }
        resp = client.post("/api/quality-score", json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "overall" in data
        assert data["completeness"] == 100.0

    def test_prioritize_endpoint(self, client):
        payload = {
            "rows": [
                {"address": "123 Main", "borough": "MANHATTAN", "severity_rating": 8,
                 "description": "Cracked sidewalk"},
            ]
        }
        resp = client.post("/api/prioritize", json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["summary"]["total_locations"] == 1

    def test_triage_endpoint(self, client):
        payload = {
            "rows": [
                {"complaint_text": "Dangerous trip hazard, someone fell"},
            ],
            "text_column": "complaint_text",
        }
        resp = client.post("/api/triage", json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1

    def test_board_endpoint(self, client):
        resp = client.get("/api/board")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "stats" in data

    def test_create_task_endpoint(self, client):
        payload = {"title": "Test task", "priority": "high", "category": "construction"}
        resp = client.post("/api/board/task", json=payload)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["title"] == "Test task"

    def test_kpis_endpoint(self, client):
        resp = client.get("/api/kpis")
        assert resp.status_code == 200
