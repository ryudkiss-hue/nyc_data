"""Readiness scoring and doctor integration."""

from __future__ import annotations

import json

from socrata_toolkit.core.readiness import run_readiness_checks


def test_readiness_report_structure():
    report = run_readiness_checks()
    assert report["overall_score"] >= 95
    assert report.get("grade") == "agency_ready"
    assert "overall_score" in report
    assert "axis_scores" in report
    assert "axes" in report
    for axis in (
        "accessibility",
        "functionality",
        "presentation",
        "packaging",
        "reliability",
        "documentation",
        "security",
        "performance",
        "job_fit",
    ):
        assert axis in report["axes"]
        assert axis in report["axis_scores"]
        assert 0 <= report["axis_scores"][axis] <= 100


def test_readiness_import_shims_pass():
    report = run_readiness_checks()
    func = report["axes"]["functionality"]
    advanced = [i for i in func if "advanced" in i["name"] or "program" in i["name"]]
    assert advanced
    assert all(i["ok"] for i in advanced)


def test_doctor_checklist_includes_readiness():
    from click.testing import CliRunner
    from socrata_toolkit.core.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["doctor", "--checklist"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "readiness" in data
    assert data["readiness"]["overall_score"] >= 90
    func = data["readiness"]["axes"]["functionality"]
    assert any(i["name"] == "datasets_yaml" and i["ok"] for i in func)
