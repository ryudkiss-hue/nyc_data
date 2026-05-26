"""End-to-end tests for Analyst Autopilot workflow."""



from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from socrata_toolkit.analyst import run_analyst_pack
from socrata_toolkit.analyst.diff import diff_construction_lists

FIXTURES = Path(__file__).parent / "fixtures" / "analyst"





@pytest.fixture(scope="module", autouse=True)

def _ensure_fixtures():

    if not (FIXTURES / "inspections.xlsx").exists():

        from tests.fixtures.analyst.generate_fixtures import write_fixtures



        write_fixtures()





@pytest.fixture

def analyst_profile(tmp_path) -> Path:

    profile = {

        "profile_name": "test_sidewalk",

        "offline": True,

        "budget_codes": str(Path(__file__).resolve().parents[1] / "config" / "budget_codes.yaml"),

        "sources": {

            "inspections": {

                "type": "excel",

                "path": str(FIXTURES / "inspections.xlsx"),

                "sheet": 0,

            },

            "contracts": {

                "type": "excel",

                "path": str(FIXTURES / "contracts.xlsx"),

                "sheet": 0,

            },

            "permits": {

                "type": "excel",

                "path": str(FIXTURES / "permits.xlsx"),

                "sheet": 0,

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

        "contract_ids": ["C-100"],

        "inquiry_templates_dir": str(

            Path(__file__).resolve().parents[1] / "config" / "inquiry_templates"

        ),

    }

    path = tmp_path / "profile.yaml"

    path.write_text(yaml.dump(profile), encoding="utf-8")

    return path





def test_analyst_dry_run(analyst_profile):

    result = run_analyst_pack(analyst_profile, dry_run=True)

    assert result.dry_run is True

    assert len(result.warnings) >= 3

    manifest = json.loads(result.manifest_path().read_text(encoding="utf-8"))

    assert "sources" in manifest

    assert manifest.get("toolkit_version")





def test_analyst_pack_outputs(analyst_profile):

    result = run_analyst_pack(analyst_profile, dry_run=False)

    assert result.pack_dir.exists()

    manifest = result.pack_dir / "manifest.json"

    assert manifest.exists()

    data = json.loads(manifest.read_text(encoding="utf-8"))

    assert data["profile_name"] == "test_sidewalk"

    assert data.get("toolkit_version")

    assert "sources" in data

    assert "started_at" in data

    assert "inspections" in data["sources"]

    assert (result.pack_dir / "construction_list.xlsx").exists() or "construction_list" in result.artifacts

    assert (result.pack_dir / "executive_summary.html").exists()

    assert (result.pack_dir / "executive_summary.md").exists()

    conflicts = result.pack_dir / "conflicts_summary.md"

    if conflicts.exists():

        text = conflicts.read_text(encoding="utf-8")

        assert "Conflicts" in text or "conflict" in text.lower()

    review = result.pack_dir / "conflicts_review.xlsx"

    assert review.exists()

    contract_md = result.pack_dir / "contract_status.md"

    if contract_md.exists():

        assert len(contract_md.read_text(encoding="utf-8")) > 20

    kpi = result.pack_dir / "program_kpi.json"

    if kpi.exists():

        kpi_data = json.loads(kpi.read_text(encoding="utf-8"))

        assert "overall_health" in kpi_data





def test_construction_diff(tmp_path):

    out = tmp_path / "pack"

    prev = pd.DataFrame({"location_id": ["L001", "L002"]})

    cur = pd.DataFrame({"location_id": ["L001", "L003"]})

    tagged, md = diff_construction_lists(cur, prev)

    assert "Added" in md

    assert "L003" in md

    assert tagged.loc[tagged["location_id"] == "L003", "_wow_change"].iloc[0] == "new"





def test_partial_failure_continues(tmp_path):

    profile = {

        "profile_name": "partial_test",

        "offline": True,

        "sources": {

            "inspections": {

                "type": "excel",

                "path": str(FIXTURES / "inspections.xlsx"),

            },

            "broken": {"type": "unknown_source_type"},

        },

        "outputs": {"dir": str(tmp_path / "analyst_pack")},

        "steps": {"prioritize": True, "executive_summary": False, "inquiry_templates": False},

    }

    path = tmp_path / "profile_partial.yaml"

    path.write_text(yaml.dump(profile), encoding="utf-8")

    result = run_analyst_pack(path, dry_run=False)

    manifest = json.loads(result.manifest_path().read_text(encoding="utf-8"))

    assert manifest["partial_failures"]

    assert manifest["sources"]["inspections"]["status"] == "ok"

    assert (result.pack_dir / "construction_list.xlsx").exists()





def test_offline_skips_socrata(tmp_path):

    profile = {

        "profile_name": "offline_test",

        "offline": True,

        "sources": {

            "inspections": {

                "type": "socrata",

                "domain": "data.cityofnewyork.us",

                "fourfour": "erm2-nwe9",

            },

            "contracts": {

                "type": "excel",

                "path": str(FIXTURES / "contracts.xlsx"),

            },

        },

        "outputs": {"dir": str(tmp_path / "analyst_pack")},

        "steps": {"prioritize": False, "executive_summary": False},

    }

    path = tmp_path / "offline.yaml"

    path.write_text(yaml.dump(profile), encoding="utf-8")

    result = run_analyst_pack(path, dry_run=True)

    assert any("offline" in w.lower() for w in result.warnings)


