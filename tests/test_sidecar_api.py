"""Tests for the local-only FastAPI sidecar service.

These verify the module imports cleanly with only fastapi/pydantic present and
that endpoints degrade gracefully when optional deps are absent.
"""

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from app.sidecar_api import app  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "uptime_s" in body
    caps = body["capabilities"]
    assert isinstance(caps, dict)
    for key in ("pymc", "prophet", "privacy", "fair", "dmbok"):
        assert key in caps
        assert isinstance(caps[key], bool)


def test_bayesian_yield_rate_posterior():
    r = client.post(
        "/api/bayesian/yield-rate",
        json={"observations": [8, 9, 7], "totals": [10, 10, 10], "draws": 300},
    )
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["mean"] <= 1.0
    assert 0.0 <= body["hdi_3"] <= body["hdi_97"] <= 1.0
    assert body["hdi_3"] <= body["mean"] <= body["hdi_97"]
    assert body["method"] in ("advi", "bootstrap")
    assert len(body["samples"]) <= 200
    assert all(0.0 <= s <= 1.0 for s in body["samples"])


def test_bayesian_yield_rate_validation():
    r = client.post(
        "/api/bayesian/yield-rate",
        json={"observations": [1, 2], "totals": [10]},
    )
    assert r.status_code == 400


def test_anomalies_flags_outlier():
    # One obvious outlier among many tightly-clustered points so the simple
    # population z-score exceeds 3.
    values = [1.0, 1.1, 0.9, 1.05, 0.95, 1.0, 1.02, 0.98, 1.01, 0.99] * 3 + [200.0]
    r = client.post("/api/quality/anomalies", json={"values": values})
    assert r.status_code == 200
    body = r.json()
    outlier_idx = len(values) - 1
    assert outlier_idx in body["indices"]
    assert body["method"] == "zscore"


def test_anomalies_no_outlier():
    r = client.post("/api/quality/anomalies", json={"values": [1.0, 1.0, 1.0, 1.0]})
    assert r.status_code == 200
    assert r.json()["indices"] == []


def test_prophet_endpoint_present_or_absent():
    r = client.post(
        "/api/forecast/prophet",
        json={
            "dates": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "values": [1.0, 2.0, 3.0],
            "periods": 5,
        },
    )
    assert r.status_code in (200, 503)


def test_prophet_length_mismatch():
    r = client.post(
        "/api/forecast/prophet",
        json={"dates": ["2024-01-01", "2024-01-02"], "values": [1.0]},
    )
    # 400 (validation) preferred; pydantic min_length may yield 422.
    assert r.status_code in (400, 422)


def test_pii_scan_present_or_absent():
    r = client.post(
        "/api/governance/pii-scan",
        json={"rows": [{"email": "a@b.com"}, {"email": "c@d.com"}]},
    )
    assert r.status_code in (200, 503)


def test_dmbok_present_or_absent():
    r = client.post(
        "/api/governance/dmbok",
        json={"rows": [{"id": 1, "name": "x"}, {"id": 2, "name": "y"}]},
    )
    assert r.status_code in (200, 503)


def test_fairness_present_or_absent():
    r = client.post(
        "/api/governance/fairness",
        json={"title": "Test", "description": "d", "license": "CC0"},
    )
    assert r.status_code in (200, 503)
