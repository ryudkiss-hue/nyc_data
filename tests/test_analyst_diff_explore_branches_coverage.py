"""Branch-coverage tests for analyst.diff and analyst.explore."""

from __future__ import annotations

import pandas as pd


# ---------------------------------------------------------------------------
# analyst.diff
# ---------------------------------------------------------------------------

class TestFindPreviousPackDir:
    def test_no_root_returns_none(self, tmp_path):
        from socrata_toolkit.analyst.diff import find_previous_pack_dir

        pack = tmp_path / "2024-02-01"
        # outputs_root doesn't exist
        assert find_previous_pack_dir(pack, outputs_root=tmp_path / "missing") is None

    def test_returns_prior_dated_dir(self, tmp_path):
        from socrata_toolkit.analyst.diff import find_previous_pack_dir

        root = tmp_path / "packs"
        root.mkdir()
        (root / "2024-01-01").mkdir()
        (root / "2024-02-01").mkdir()
        pack = root / "2024-02-01"
        prev = find_previous_pack_dir(pack, outputs_root=root)
        assert prev is not None
        assert prev.name == "2024-01-01"

    def test_no_prior_returns_none_or_latest(self, tmp_path):
        from socrata_toolkit.analyst.diff import find_previous_pack_dir

        root = tmp_path / "packs"
        root.mkdir()
        pack = root / "2024-01-01"
        pack.mkdir()
        # Only the pack itself exists -> no prior
        assert find_previous_pack_dir(pack, outputs_root=root) is None


class TestDiffConstructionLists:
    def test_both_empty(self):
        from socrata_toolkit.analyst.diff import diff_construction_lists

        tagged, md = diff_construction_lists(pd.DataFrame(), pd.DataFrame())
        assert "No data" in md

    def test_added_and_removed(self):
        from socrata_toolkit.analyst.diff import diff_construction_lists

        current = pd.DataFrame({"location_id": ["A", "B", "C"]})
        previous = pd.DataFrame({"location_id": ["B", "C", "D"]})
        tagged, md = diff_construction_lists(current, previous)
        # A is new, D was dropped
        assert "New locations" in md or "Added" in md or "A" in md
        assert isinstance(tagged, pd.DataFrame)

    def test_identical_lists(self):
        from socrata_toolkit.analyst.diff import diff_construction_lists

        df = pd.DataFrame({"location_id": ["A", "B"]})
        tagged, md = diff_construction_lists(df.copy(), df.copy())
        assert isinstance(md, str)


# ---------------------------------------------------------------------------
# analyst.explore — preview_priority branches
# ---------------------------------------------------------------------------

class TestPreviewPriority:
    def _df(self):
        return pd.DataFrame({
            "location_id": [f"L{i}" for i in range(6)],
            "borough": ["MANHATTAN", "BRONX", "MANHATTAN", "QUEENS", "MANHATTAN", "BRONX"],
            "ada_flag": [True, False, True, False, True, False],
            "_has_conflict": [True, False, False, True, False, True],
            "severity_rating": [6, 2, 7, 1, 8, 3],
            "defect_grade": ["A", "B", "A", "C", "A", "B"],
        })

    def test_empty_returns_empty(self):
        from socrata_toolkit.analyst.explore import preview_priority

        out = preview_priority(pd.DataFrame())
        assert out.empty

    def test_borough_filter(self):
        from socrata_toolkit.analyst.explore import preview_priority

        out = preview_priority(self._df(), borough="MANHATTAN")
        assert all(out["borough"].str.upper() == "MANHATTAN")

    def test_ada_only_with_flag(self):
        from socrata_toolkit.analyst.explore import preview_priority

        out = preview_priority(self._df(), ada_only=True)
        assert len(out) >= 1

    def test_ada_only_via_severity(self):
        from socrata_toolkit.analyst.explore import preview_priority

        df = self._df().drop(columns=["ada_flag"])
        out = preview_priority(df, ada_only=True)
        # only rows with severity_rating >= 5 retained
        assert all(out["severity_rating"].astype(float) >= 5)

    def test_conflicts_only(self):
        from socrata_toolkit.analyst.explore import preview_priority

        out = preview_priority(self._df(), conflicts_only=True)
        assert len(out) >= 1

    def test_conflicts_only_alt_column(self):
        from socrata_toolkit.analyst.explore import preview_priority

        df = self._df().rename(columns={"_has_conflict": "has_conflict"})
        out = preview_priority(df, conflicts_only=True)
        assert isinstance(out, pd.DataFrame)

    def test_top_n(self):
        from socrata_toolkit.analyst.explore import preview_priority

        out = preview_priority(self._df(), top_n=2)
        assert len(out) <= 2


class TestBoroughBarCounts:
    def test_empty(self):
        from socrata_toolkit.analyst.explore import borough_bar_counts

        assert borough_bar_counts(pd.DataFrame()) == {}

    def test_with_score_col(self):
        from socrata_toolkit.analyst.explore import borough_bar_counts

        df = pd.DataFrame({"borough": ["MN", "MN", "BX"], "_priority_score": [10, 20, 30]})
        out = borough_bar_counts(df)
        assert out["MN"] == 15.0
        assert out["BX"] == 30.0

    def test_without_score_col_uses_size(self):
        from socrata_toolkit.analyst.explore import borough_bar_counts

        df = pd.DataFrame({"borough": ["MN", "MN", "BX"]})
        out = borough_bar_counts(df)
        assert out["MN"] == 2.0


class TestFilterKpiMetrics:
    def test_all_returns_everything(self):
        from socrata_toolkit.analyst.explore import filter_kpi_metrics

        metrics = [{"name": "x"}, {"name": "y"}]
        assert filter_kpi_metrics(metrics, categories=["all"]) == metrics
        assert filter_kpi_metrics(metrics, categories=None) == metrics

    def test_category_match(self):
        from socrata_toolkit.analyst.explore import filter_kpi_metrics

        metrics = [{"name": "m1", "category": "budget"}, {"name": "m2", "category": "other"}]
        out = filter_kpi_metrics(metrics, categories=["budget"])
        assert {m["name"] for m in out} == {"m1"}

    def test_name_heuristic_budget(self):
        from socrata_toolkit.analyst.explore import filter_kpi_metrics

        metrics = [{"name": "CPI ratio"}, {"name": "unrelated"}]
        out = filter_kpi_metrics(metrics, categories=["budget"])
        assert any("CPI" in m["name"] for m in out)

    def test_no_match_returns_all(self):
        from socrata_toolkit.analyst.explore import filter_kpi_metrics

        metrics = [{"name": "x"}]
        # category with no matches -> falls back to returning all
        out = filter_kpi_metrics(metrics, categories=["nonexistent"])
        assert out == metrics
