from __future__ import annotations

import json
from pathlib import Path

import yaml

from socrata_toolkit.analyst.publish import load_publish_profile, publish_pack


def _make_pack(tmp_path: Path) -> Path:
    pack = tmp_path / "outputs" / "analyst_pack" / "2099-01-01"
    pack.mkdir(parents=True, exist_ok=True)
    (pack / "manifest.json").write_text(
        json.dumps({"profile_name": "test_profile", "run_date": "2099-01-01", "artifacts": {}}),
        encoding="utf-8",
    )
    (pack / "executive_summary.md").write_text("# Executive Summary\n\nHello world.", encoding="utf-8")
    (pack / "program_kpi.json").write_text(json.dumps({"overall_health": "green"}), encoding="utf-8")
    return pack

def test_load_publish_profile(tmp_path: Path):
    p = tmp_path / "publish.yaml"
    p.write_text("profile_name: demo\nfile_copy:\n  enabled: true\n  dest_root: X:/share\n", encoding="utf-8")
    data = load_publish_profile(p)
    assert data["profile_name"] == "demo"
    assert data["file_copy"]["enabled"] is True

def test_publish_dry_run_generates_report(tmp_path: Path):
    pack = _make_pack(tmp_path)
    profile = tmp_path / "publish.yaml"
    profile.write_text(
        yaml.dump(
            {
                "profile_name": "demo",
                "file_copy": {"enabled": True, "dest_root": str(tmp_path / "dest")},
                "bi_export": {"enabled": True, "dest_root": str(tmp_path / "bi"), "include": ["program_kpi.json"]},
                "teams": {"enabled": True, "webhook_env": "MISSING_TEAMS_WEBHOOK"},
                "email": {"enabled": True, "to": []},
                "pptx": {"enabled": True, "template_path": "missing.pptx"},
            }
        ),
        encoding="utf-8",
    )
    report = publish_pack(pack_dir=pack, profile_path=profile, dry_run=True, state_path=str(tmp_path / "state.json"))
    d = report.to_dict()
    assert d["dry_run"] is True
    kinds = [a["kind"] for a in d["actions"]]
    assert "file_copy" in kinds
    assert "bi_export" in kinds

