"""Tests for improvement batch (Groups 1–9)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# GROUP 2 — ML analysis modules
# ---------------------------------------------------------------------------

def test_incremental_model_learn_predict():
    pytest.importorskip("river", reason="river not installed")
    from src.socrata_toolkit.analysis.incremental import IncrementalQualityModel
    model = IncrementalQualityModel()
    model.learn({"score": 0.8, "rows": 100}, 1)
    model.learn({"score": 0.2, "rows": 5}, 0)
    result = model.predict({"score": 0.9, "rows": 200})
    assert result in (0, 1)


def test_semantic_search_index_and_query():
    pytest.importorskip("sentence_transformers", reason="sentence-transformers not installed")
    from src.socrata_toolkit.analysis.semantic_search import SemanticCatalogSearch
    searcher = SemanticCatalogSearch()
    records = [
        {"name": "sidewalk inspections", "id": "a"},
        {"name": "pothole complaints", "id": "b"},
        {"name": "street lighting", "id": "c"},
    ]
    searcher.index(records)
    results = searcher.search("sidewalk repair", top_k=2)
    assert len(results) <= 2
    assert all("score" in r for r in results)


# ---------------------------------------------------------------------------
# Sidecar TestClient fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def sidecar_client():
    from app.sidecar_api import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# GROUP 4 — Governance endpoints
# ---------------------------------------------------------------------------

def test_dcat3_endpoint(sidecar_client):
    resp = sidecar_client.get("/api/governance/dcat3")
    assert resp.status_code == 200
    data = resp.json()
    assert "@context" in data
    assert data["@type"] == "dcat:Catalog"


def test_provenance_endpoint(sidecar_client):
    resp = sidecar_client.get("/api/governance/provenance")
    assert resp.status_code == 200
    data = resp.json()
    assert "@context" in data


def test_odrl_policy_endpoint(sidecar_client):
    resp = sidecar_client.get("/api/governance/odrl-policy")
    assert resp.status_code == 200
    data = resp.json()
    assert "@context" in data or "odrl:permission" in data


# ---------------------------------------------------------------------------
# GROUP 7 — STAC / OGC endpoints
# ---------------------------------------------------------------------------

def test_stac_catalog_endpoint(sidecar_client):
    resp = sidecar_client.get("/api/stac/catalog")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("type") == "Catalog"
    assert "stac_version" in data


def test_ogc_collections_endpoint(sidecar_client):
    resp = sidecar_client.get("/api/ogc/collections")
    assert resp.status_code == 200
    data = resp.json()
    assert "collections" in data


# ---------------------------------------------------------------------------
# GROUP 2 — DP histogram endpoint
# ---------------------------------------------------------------------------

def test_dp_histogram_endpoint(sidecar_client):
    payload = {"values": [1.0, 2.0, 3.0, 2.5, 1.5, 3.5, 2.2, 2.8], "epsilon": 1.0}
    resp = sidecar_client.post("/api/analysis/dp-histogram", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "bins" in data
    assert len(data["bins"]) > 0
    assert all("bin" in b and "count" in b for b in data["bins"])
    assert "method" in data
