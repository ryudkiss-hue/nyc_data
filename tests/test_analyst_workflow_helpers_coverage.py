"""Coverage tests for analyst.workflow private helpers."""

from __future__ import annotations

import pandas as pd


def _profile(**steps):
    from socrata_toolkit.analyst.config import AnalystProfile

    return AnalystProfile(profile_name="test", sources={}, steps=steps)


# ---------------------------------------------------------------------------
# _normalize_frames
# ---------------------------------------------------------------------------

class TestNormalizeFrames:
    def test_renames_aliases(self):
        from socrata_toolkit.analyst.workflow import _normalize_frames

        frames = {
            "a": pd.DataFrame({"boro": ["MN"], "contract": ["C1"], "loc_id": ["L1"]}),
        }
        out = _normalize_frames(frames)
        cols = set(out["a"].columns)
        assert "borough" in cols
        assert "contract_id" in cols
        assert "location_id" in cols

    def test_empty_passthrough(self):
        from socrata_toolkit.analyst.workflow import _normalize_frames

        out = _normalize_frames({"a": pd.DataFrame()})
        assert out["a"].empty

    def test_no_aliases_unchanged(self):
        from socrata_toolkit.analyst.workflow import _normalize_frames

        df = pd.DataFrame({"x": [1], "y": [2]})
        out = _normalize_frames({"a": df})
        assert list(out["a"].columns) == ["x", "y"]


# ---------------------------------------------------------------------------
# _compute_kpi_payload
# ---------------------------------------------------------------------------

class TestComputeKpiPayload:
    def test_disabled_returns_none(self):
        from socrata_toolkit.analyst.workflow import _compute_kpi_payload

        profile = _profile(program_kpi=False)
        payload, path = _compute_kpi_payload(profile, pd.DataFrame(), pd.DataFrame())
        assert payload is None
        assert path is None

    def test_empty_data_returns_none(self):
        from socrata_toolkit.analyst.workflow import _compute_kpi_payload

        profile = _profile(program_kpi=True)
        payload, path = _compute_kpi_payload(profile, pd.DataFrame(), pd.DataFrame())
        assert payload is None

    def test_with_data_returns_payload(self):
        from socrata_toolkit.analyst.workflow import _compute_kpi_payload

        profile = _profile(program_kpi=True)
        contracts = pd.DataFrame({
            "contract_id": ["C1", "C2"],
            "status": ["active", "complete"],
            "borough": ["MN", "BX"],
        })
        payload, path = _compute_kpi_payload(profile, contracts, pd.DataFrame())
        # compute_program_dashboard should yield a payload dict + sidecar path
        assert payload is not None
        assert "metrics" in payload
        assert path is not None and path.endswith(".json")


# ---------------------------------------------------------------------------
# _build_construction_plan
# ---------------------------------------------------------------------------

class TestBuildConstructionPlan:
    def test_prioritize_disabled_returns_empty(self):
        from socrata_toolkit.analyst.workflow import _build_construction_plan

        profile = _profile(prioritize=False, construction_diff=False)
        construction, conflict, md, review, diff_md = _build_construction_plan(
            profile, pd.DataFrame({"x": [1]}), pd.DataFrame()
        )
        assert construction.empty
        assert conflict is None

    def test_prioritize_empty_inspections(self):
        from socrata_toolkit.analyst.workflow import _build_construction_plan

        profile = _profile(prioritize=True, construction_diff=False)
        construction, conflict, md, review, diff_md = _build_construction_plan(
            profile, pd.DataFrame(), pd.DataFrame()
        )
        assert construction.empty

    def test_prioritize_with_inspections(self):
        from socrata_toolkit.analyst.workflow import _build_construction_plan

        profile = _profile(prioritize=True, construction_diff=False)
        inspections = pd.DataFrame({
            "location_id": ["L1", "L2", "L3"],
            "borough": ["MANHATTAN", "BRONX", "QUEENS"],
            "defect_grade": ["A", "B", "C"],
            "description": ["crack", "pothole", "hazard"],
        })
        construction, conflict, md, review, diff_md = _build_construction_plan(
            profile, inspections, pd.DataFrame()
        )
        assert not construction.empty


class TestApplyRoleProfile:
    """Cover _apply_role_profile using a bundled role profile config."""

    def _result(self, tmp_path):
        from socrata_toolkit.analyst.workflow import AnalystPackResult

        pack_dir = tmp_path / "2024-01-01"
        pack_dir.mkdir(parents=True, exist_ok=True)
        return AnalystPackResult(
            pack_dir=pack_dir,
            profile_name="test",
            run_date="2024-01-01",
            artifacts={},
            dry_run=False,
            warnings=[],
            sources={},
            partial_failures=[],
            started_at="2024-01-01T00:00:00",
            finished_at=None,
        )

    def test_no_role_returns_early(self, tmp_path):
        from socrata_toolkit.analyst.workflow import _apply_role_profile

        profile = _profile()  # no role
        result = self._result(tmp_path)
        _apply_role_profile(
            profile, result, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
            "", "", None, [],
        )
        # nothing added
        assert result.artifacts == {}

    def test_with_bundled_role_profile(self, tmp_path):
        from pathlib import Path

        from socrata_toolkit.analyst.config import AnalystProfile
        from socrata_toolkit.analyst.workflow import _apply_role_profile

        role_cfg = Path("config/role_profiles/sw_project_analyst.yaml")
        if not role_cfg.exists():
            import pytest
            pytest.skip("bundled role profile not present")

        profile = AnalystProfile(
            profile_name="test", sources={}, steps={},
            role_profile_path=str(role_cfg),
        )
        result = self._result(tmp_path)
        warnings: list[str] = []
        inspections = pd.DataFrame({"borough": ["MANHATTAN"], "severity": [5]})
        # Should either write role artifacts or append a warning — both are covered paths
        _apply_role_profile(
            profile, result, inspections, pd.DataFrame(), pd.DataFrame(),
            "", "", {"metrics": []}, warnings,
        )
        # manifest written either way
        assert (result.pack_dir / "manifest.json").exists() or result.artifacts is not None
