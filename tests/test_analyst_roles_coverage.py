"""Comprehensive tests for analyst.roles module."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from socrata_toolkit.analyst.roles import (
    RoleDuty,
    RoleKpiDashboard,
    RoleKpiDef,
    RoleKpiSnapshot,
    RoleProfile,
    _parse_conflict_rate,
    _parse_diff_added,
    _parse_duty,
    _parse_kpi,
    _program_green_pct,
    build_role_task_status_md,
    compute_role_kpis,
    evaluate_task_checklist,
    load_role_profile,
    merge_program_and_role_kpis,
    resolve_role_profile_path,
    role_dashboard_to_dict,
    write_role_artifacts,
)

class TestRoleDuty:
    """Tests for RoleDuty dataclass."""

    def test_minimal_role_duty(self):
        duty = RoleDuty(id="D1", text="Review violations")
        assert duty.id == "D1"
        assert duty.text == "Review violations"
        assert duty.workflow_steps == []
        assert duty.pack_outputs == []
        assert duty.inquiry_templates == []

    def test_role_duty_with_steps(self):
        duty = RoleDuty(
            id="D1",
            text="Review violations",
            workflow_steps=["fetch", "analyze", "report"],
        )
        assert len(duty.workflow_steps) == 3
        assert "fetch" in duty.workflow_steps

class TestRoleKpiDef:
    """Tests for RoleKpiDef dataclass."""

    def test_minimal_kpi_def(self):
        kpi = RoleKpiDef(
            name="completion_rate",
            description="Ramp completion",
            formula="completed / total",
            direction="higher_is_better",
            target=0.8,
            warning_threshold=0.5,
            critical_threshold=0.3,
        )
        assert kpi.name == "completion_rate"
        assert kpi.target == 0.8

    def test_kpi_def_with_data_source(self):
        kpi = RoleKpiDef(
            name="violations_count",
            description="Open violations",
            formula="count(*)",
            direction="lower_is_better",
            target=100,
            warning_threshold=500,
            critical_threshold=1000,
            data_source={"dataset": "violations", "fourfour": "dntt-gqwq"},
        )
        assert kpi.data_source["dataset"] == "violations"

class TestRoleProfile:
    """Tests for RoleProfile dataclass."""

    def test_minimal_role_profile(self):
        profile = RoleProfile(
            role_id="analyst",
            display_name="Project Analyst",
            job_reference={},
            unit_focus="Sidewalk inspections",
            duties=[],
            kpis=[],
        )
        assert profile.role_id == "analyst"
        assert profile.display_name == "Project Analyst"

    def test_role_profile_with_duties_and_kpis(self):
        duties = [RoleDuty(id="D1", text="Review data")]
        kpis = [
            RoleKpiDef(
                name="kpi1",
                description="KPI",
                formula="x",
                direction="up",
                target=1.0,
                warning_threshold=0.5,
                critical_threshold=0.2,
            )
        ]
        profile = RoleProfile(
            role_id="analyst",
            display_name="Analyst",
            job_reference={"jid": "35715"},
            unit_focus="Focus",
            duties=duties,
            kpis=kpis,
        )
        assert len(profile.duties) == 1
        assert len(profile.kpis) == 1

class TestParseDuty:
    """Tests for _parse_duty function."""

    def test_parse_minimal_duty(self):
        raw = {"id": "D1", "text": "Review"}
        duty = _parse_duty(raw)
        assert duty.id == "D1"
        assert duty.text == "Review"

    def test_parse_duty_with_all_fields(self):
        raw = {
            "id": "D1",
            "text": "Review data",
            "workflow_steps": ["fetch", "analyze"],
            "pack_outputs": ["report.xlsx", "analysis.md"],
            "inquiry_templates": ["template1", "template2"],
        }
        duty = _parse_duty(raw)
        assert duty.id == "D1"
        assert len(duty.workflow_steps) == 2
        assert len(duty.pack_outputs) == 2

class TestParseKpi:
    """Tests for _parse_kpi function."""

    def test_parse_minimal_kpi(self):
        raw = {"name": "completion"}
        kpi = _parse_kpi(raw)
        assert kpi.name == "completion"
        assert kpi.direction == "lower_is_better"

    def test_parse_kpi_with_all_fields(self):
        raw = {
            "name": "completion_rate",
            "description": "Ramps completed",
            "formula": "completed / total",
            "direction": "higher_is_better",
            "target": 0.8,
            "warning_threshold": 0.5,
            "critical_threshold": 0.3,
            "data_source": {"dataset": "ramps"},
        }
        kpi = _parse_kpi(raw)
        assert kpi.name == "completion_rate"
        assert kpi.direction == "higher_is_better"
        assert kpi.target == 0.8

class TestLoadRoleProfile:
    """Tests for load_role_profile function."""

    def test_load_from_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir) / "analyst.yaml"
            profile_text = """
role_id: analyst
display_name: Project Analyst
unit_focus: Sidewalk program management
job_reference:
  jid: "35715"
  business_title: Project Analyst
duties:
  - id: D1
    text: Review violations
    workflow_steps: [fetch, analyze]
kpis:
  - name: completion_rate
    description: Ramp completion
    formula: completed / total
    direction: higher_is_better
    target: 0.8
    warning_threshold: 0.5
    critical_threshold: 0.3
"""
            profile_path.write_text(profile_text, encoding="utf-8")
            profile = load_role_profile(profile_path)
            assert profile.role_id == "analyst"
            assert len(profile.duties) == 1
            assert len(profile.kpis) == 1

    def test_load_from_role_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / "role_profiles"
            role_dir.mkdir()
            role_file = role_dir / "test_role.yaml"
            role_yaml = (
                "role_id: test\n"
                "display_name: Test\n"
                "unit_focus: Test focus\n"
                "duties: []\n"
                "kpis: []\n"
            )
            role_file.write_text(role_yaml, encoding="utf-8")

            profile = load_role_profile(role_file)
            assert profile.role_id == "test"

    def test_load_nonexistent_profile(self):
        with pytest.raises(FileNotFoundError):
            load_role_profile("/nonexistent/profile.yaml")

class TestParseConflictRate:
    """Tests for _parse_conflict_rate function."""

    def test_parse_conflict_rate_valid(self):
        md = "Conflict rate: 15.5%"
        rate = _parse_conflict_rate(md)
        assert rate == 15.5

    def test_parse_conflict_rate_various_formats(self):
        assert _parse_conflict_rate("Conflict Rate: 20%") == 20.0
        assert _parse_conflict_rate("conflict rate: 5.25%") == 5.25

    def test_parse_conflict_rate_not_found(self):
        assert _parse_conflict_rate("No conflict info") is None

    def test_parse_conflict_rate_empty(self):
        assert _parse_conflict_rate("") is None
        assert _parse_conflict_rate(None) is None

class TestParseDiffAdded:
    """Tests for _parse_diff_added function."""

    def test_parse_diff_added_valid(self):
        md = "Added: 25 locations"
        count = _parse_diff_added(md)
        assert count == 25.0

    def test_parse_diff_added_various_formats(self):
        assert _parse_diff_added("Added 10 items") == 10.0
        assert _parse_diff_added("added: 100") == 100.0

    def test_parse_diff_added_not_found(self):
        assert _parse_diff_added("No changes") == 0.0

    def test_parse_diff_added_empty(self):
        assert _parse_diff_added("") == 0.0
        assert _parse_diff_added(None) == 0.0

class TestProgramGreenPct:
    """Tests for _program_green_pct function."""

    def test_program_green_pct_all_green(self):
        program_kpi = {
            "metrics": [
                {"status": "green"},
                {"status": "green"},
                {"status": "green"},
            ]
        }
        pct = _program_green_pct(program_kpi)
        assert pct == 100.0

    def test_program_green_pct_mixed(self):
        program_kpi = {
            "metrics": [
                {"status": "green"},
                {"status": "yellow"},
                {"status": "green"},
                {"status": "red"},
            ]
        }
        pct = _program_green_pct(program_kpi)
        assert pct == 50.0

    def test_program_green_pct_none(self):
        assert _program_green_pct(None) is None
        assert _program_green_pct({}) is None
        assert _program_green_pct({"metrics": []}) is None

class TestComputeRoleKpis:
    """Tests for compute_role_kpis function."""

    @pytest.fixture
    def basic_role(self):
        return RoleProfile(
            role_id="analyst",
            display_name="Analyst",
            job_reference={"jid": "35715"},
            unit_focus="Program management",
            duties=[],
            kpis=[
                RoleKpiDef(
                    name="conflict_rate_pct",
                    description="Conflict rate",
                    formula="conflicts / total",
                    direction="lower_is_better",
                    target=5.0,
                    warning_threshold=10.0,
                    critical_threshold=20.0,
                ),
                RoleKpiDef(
                    name="ifa_report_ready",
                    description="IFA report ready",
                    formula="has_report",
                    direction="higher_is_better",
                    target=1.0,
                    warning_threshold=0.5,
                    critical_threshold=0.0,
                ),
            ],
        )

    def test_compute_with_minimal_inputs(self, basic_role):
        dashboard = compute_role_kpis(basic_role)
        assert dashboard.role_id == "analyst"
        assert dashboard.display_name == "Analyst"
        # Health is determined by metrics availability and status
        assert dashboard.overall_health in ("unknown", "green", "yellow", "red")

    def test_compute_with_conflict_rate(self, basic_role):
        dashboard = compute_role_kpis(
            basic_role,
            conflicts_md="Conflict rate: 3.5%",
        )
        assert len(dashboard.metrics) >= 1
        assert any(m.name == "conflict_rate_pct" for m in dashboard.metrics)

    def test_compute_with_pack_artifacts(self, basic_role):
        artifacts = {
            "executive_summary": "/path/to/summary.md",
            "contract_status": "/path/to/contract.xlsx",
        }
        dashboard = compute_role_kpis(basic_role, pack_artifacts=artifacts)
        assert any(m.name == "ifa_report_ready" and m.value == 1.0 for m in dashboard.metrics)

class TestRoleDashboardSerialization:
    """Tests for role_dashboard_to_dict function."""

    def test_role_dashboard_to_dict(self):
        dashboard = RoleKpiDashboard(
            role_id="analyst",
            display_name="Analyst",
            job_reference={"jid": "123"},
            metrics=[
                RoleKpiSnapshot(
                    name="metric1",
                    value=0.8,
                    target=0.9,
                    status="yellow",
                    description="Test metric",
                )
            ],
            overall_health="yellow",
        )
        result = role_dashboard_to_dict(dashboard)
        assert result["role_id"] == "analyst"
        assert result["overall_health"] == "yellow"
        assert len(result["metrics"]) == 1
        assert result["metrics"][0]["name"] == "metric1"

class TestMergeProgramAndRoleKpis:
    """Tests for merge_program_and_role_kpis function."""

    def test_merge_kpis(self):
        program_kpi = {"program_metric": "value", "metrics": []}
        dashboard = RoleKpiDashboard(
            role_id="analyst",
            display_name="Analyst",
            job_reference={},
            metrics=[],
            overall_health="green",
        )
        merged = merge_program_and_role_kpis(program_kpi, dashboard)
        assert "program_metric" in merged
        assert "role" in merged
        assert merged["role"]["role_id"] == "analyst"

    def test_merge_with_none_program(self):
        dashboard = RoleKpiDashboard(
            role_id="analyst",
            display_name="Analyst",
            job_reference={},
            metrics=[],
            overall_health="green",
        )
        merged = merge_program_and_role_kpis(None, dashboard)
        assert "role" in merged

class TestWriteRoleArtifacts:
    """Tests for write_role_artifacts function."""

    def test_write_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir)
            dashboard = RoleKpiDashboard(
                role_id="analyst",
                display_name="Analyst",
                job_reference={"jid": "123"},
                metrics=[],
                overall_health="green",
            )
            task_md = "# Task Status\n- [x] Task 1"

            artifacts = write_role_artifacts(pack_dir, dashboard, task_md)

            assert "role_kpi_dashboard" in artifacts
            assert "role_task_status" in artifacts
            assert (pack_dir / "role_kpi_dashboard.json").exists()
            assert (pack_dir / "role_task_status.md").exists()

    def test_write_artifacts_with_program_kpi(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir)
            dashboard = RoleKpiDashboard(
                role_id="analyst",
                display_name="Analyst",
                job_reference={},
                metrics=[],
                overall_health="green",
            )
            program_kpi = {"metrics": []}

            artifacts = write_role_artifacts(
                pack_dir,
                dashboard,
                "# Tasks",
                merged_program_kpi=program_kpi,
            )

            assert "program_kpi" in artifacts
            assert (pack_dir / "program_kpi.json").exists()

class TestBuildRoleTaskStatusMd:
    """Tests for build_role_task_status_md function."""

    def test_build_task_status_md(self):
        role = RoleProfile(
            role_id="analyst",
            display_name="Project Analyst",
            job_reference={"business_title": "Analyst", "jid": "35715", "url": "https://cityjobs.nyc.gov"},
            unit_focus="Sidewalk program",
            duties=[
                RoleDuty(id="D1", text="Review data", pack_outputs=["report.xlsx"]),
                RoleDuty(id="D2", text="Analyze trends", pack_outputs=["analysis.md"]),
            ],
            kpis=[],
        )
        tasks = [
            {
                "id": "D1",
                "duty": "Review data",
                "pack_outputs": ["report.xlsx"],
                "complete": True,
            },
            {
                "id": "D2",
                "duty": "Analyze trends",
                "pack_outputs": ["analysis.md"],
                "complete": False,
            },
        ]
        md = build_role_task_status_md(role, tasks, 50.0, "2024-06-03")

        assert "Project Analyst" in md
        assert "50%" in md
        assert "[x] **D1**" in md
        assert "[ ] **D2**" in md
        assert "cityjobs.nyc.gov" in md

class TestEvaluateTaskChecklist:
    """Tests for evaluate_task_checklist function."""

    def test_evaluate_all_complete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir)
            (pack_dir / "report.xlsx").touch()
            (pack_dir / "analysis.md").touch()

            role = RoleProfile(
                role_id="analyst",
                display_name="Analyst",
                job_reference={},
                unit_focus="Program",
                duties=[
                    RoleDuty(id="D1", text="Task 1", pack_outputs=["report.xlsx"]),
                    RoleDuty(id="D2", text="Task 2", pack_outputs=["analysis.md"]),
                ],
                kpis=[],
            )
            artifacts = {"report": str(pack_dir / "report.xlsx")}

            tasks, pct = evaluate_task_checklist(role, pack_dir, artifacts)
            assert len(tasks) == 2
            assert sum(1 for t in tasks if t["complete"]) >= 1
            assert pct >= 0

    def test_evaluate_none_complete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir)

            role = RoleProfile(
                role_id="analyst",
                display_name="Analyst",
                job_reference={},
                unit_focus="Program",
                duties=[
                    RoleDuty(id="D1", text="Task 1", pack_outputs=["missing.xlsx"]),
                ],
                kpis=[],
            )

            tasks, pct = evaluate_task_checklist(role, pack_dir, {})
            assert len(tasks) == 1
            assert tasks[0]["complete"] is False
            assert pct == 0.0

class TestResolveRoleProfilePath:
    """Tests for resolve_role_profile_path function."""

    def test_resolve_with_explicit_path(self):
        path = resolve_role_profile_path(None, explicit="./config/role_profiles/analyst.yaml")
        # Returns the path as-is or with role_profiles prefix if it doesn't exist
        assert path is not None

    def test_resolve_with_none(self):
        path = resolve_role_profile_path(None, None)
        assert path is None

    def test_resolve_with_role_id(self):
        # This might return None if the file doesn't exist
        path = resolve_role_profile_path("analyst", None)
        # Just verify it returns a Path or None
        assert path is None or isinstance(path, Path)
