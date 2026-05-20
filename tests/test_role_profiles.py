"""Tests for analyst role profiles and role KPI pack outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from socrata_toolkit.analyst import run_analyst_pack
from socrata_toolkit.analyst.roles import (
    compute_role_kpis,
    list_role_profiles,
    load_role_profile,
)

FIXTURES = Path(__file__).parent / "fixtures" / "analyst"
ROLES_DIR = Path(__file__).resolve().parents[1] / "config" / "role_profiles"


@pytest.fixture(scope="module", autouse=True)
def _ensure_fixtures():
    if not (FIXTURES / "inspections.xlsx").exists():
        from tests.fixtures.analyst.generate_fixtures import write_fixtures

        write_fixtures()


def test_role_profiles_load():
    profiles = list_role_profiles(ROLES_DIR)
    ids = {p.role_id for p in profiles}
    assert "sw_project_analyst" in ids
    assert "project_analyst_sw" in ids

    sw = load_role_profile(ROLES_DIR / "sw_project_analyst.yaml")
    assert sw.job_reference.get("jid") == "42159"
    assert len(sw.duties) >= 5
    assert len(sw.kpis) >= 4
    assert any(k.name == "high_priority_backlog" for k in sw.kpis)


def test_compute_role_kpis_sw_project_analyst():
    role = load_role_profile("sw_project_analyst")
    dash = compute_role_kpis(
        role,
        pack_artifacts={
            "executive_summary": "/tmp/x.html",
            "contract_status": "/tmp/y.md",
        },
        task_completion_pct=50.0,
        conflicts_md="Conflict rate: 10.0%\n",
    )
    names = {m.name for m in dash.metrics}
    assert "ifa_report_ready" in names
    assert "conflict_rate_pct" in names
    assert "administrative_review_coverage" in names


@pytest.fixture
def sw_role_profile(tmp_path) -> Path:
    profile = {
        "profile_name": "test_sw_project_analyst",
        "role": "sw_project_analyst",
        "offline": True,
        "sources": {
            "inspections": {
                "type": "excel",
                "path": str(FIXTURES / "inspections.xlsx"),
            },
            "contracts": {
                "type": "excel",
                "path": str(FIXTURES / "contracts.xlsx"),
            },
            "permits": {
                "type": "excel",
                "path": str(FIXTURES / "permits.xlsx"),
            },
        },
        "outputs": {"dir": str(tmp_path / "analyst_pack")},
        "steps": {
            "prioritize": True,
            "construction_diff": True,
            "conflicts": {"buffer_m": 20},
            "contract_report": True,
            "program_kpi": True,
            "inquiry_templates": True,
            "executive_summary": True,
        },
        "inquiry_templates_dir": str(
            Path(__file__).resolve().parents[1] / "config" / "inquiry_templates"
        ),
    }
    path = tmp_path / "profile_sw_role.yaml"
    path.write_text(yaml.dump(profile), encoding="utf-8")
    return path


def test_analyst_pack_includes_role_kpis(sw_role_profile):
    result = run_analyst_pack(sw_role_profile, dry_run=False)
    role_json = result.pack_dir / "role_kpi_dashboard.json"
    task_md = result.pack_dir / "role_task_status.md"
    assert role_json.exists(), result.artifacts
    assert task_md.exists()
    data = json.loads(role_json.read_text(encoding="utf-8"))
    assert data["role_id"] == "sw_project_analyst"
    assert data["job_reference"]["jid"] == "42159"
    assert len(data["metrics"]) >= 1
    kpi_keys = {m["name"] for m in data["metrics"]}
    assert "ifa_report_ready" in kpi_keys or "high_priority_backlog" in kpi_keys
    assert "role_kpi_dashboard" in result.artifacts
    manifest = json.loads(result.manifest_path().read_text(encoding="utf-8"))
    assert "role_kpi_dashboard" in manifest["artifacts"]
