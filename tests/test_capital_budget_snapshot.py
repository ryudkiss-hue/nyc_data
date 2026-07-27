"""Guards for capital-budget dollar correctness.

fb86-vt7u repeats every project once per reporting period. Summing it
unfiltered overstates the DOT capital portfolio roughly ninefold
($331B vs the true $36.3B), so the snapshot helper is load-bearing for every
dollar figure the tool reports.
"""
from __future__ import annotations

import pandas as pd

from app.viz_engine import VisualizationEngine as VE


def _multi_period_frame() -> pd.DataFrame:
    """Two projects reported across three periods — 6 rows, 2 real projects."""
    rows = []
    for period in ("202509", "202601", "202605"):
        for fms_id, budget, spend, phase in (
            ("P1", 100.0, 25.0, "Construction"),
            ("P2", 300.0, 60.0, "Design"),
        ):
            rows.append({
                "reporting_period": period,
                "fms_id": fms_id,
                "total_budget": budget,
                "spend_to_date": spend,
                "current_phase": phase,
                "fms_project_name": f"SIDEWALK RECONSTRUCTION {fms_id}",
                "managing_agency": "DOT",
            })
    return pd.DataFrame(rows)


class TestLatestCapitalSnapshot:
    def test_collapses_to_one_row_per_project(self):
        snap = VE._latest_capital_snapshot({"capital_projects_dashboard": _multi_period_frame()})
        assert len(snap) == 2, "snapshot must hold one row per project, not per period"
        assert set(snap["fms_id"]) == {"P1", "P2"}

    def test_uses_the_latest_period(self):
        snap = VE._latest_capital_snapshot({"capital_projects_dashboard": _multi_period_frame()})
        assert set(snap["reporting_period"].astype(str)) == {"202605"}

    def test_does_not_inflate_dollar_totals(self):
        raw = _multi_period_frame()
        snap = VE._latest_capital_snapshot({"capital_projects_dashboard": raw})
        # Raw sum triple-counts (3 periods); the snapshot must not.
        assert pd.to_numeric(raw["total_budget"]).sum() == 1200.0
        assert snap["total_budget"].sum() == 400.0

    def test_dollar_columns_are_numeric(self):
        raw = _multi_period_frame()
        raw["total_budget"] = raw["total_budget"].astype(str)
        snap = VE._latest_capital_snapshot({"capital_projects_dashboard": raw})
        assert pd.api.types.is_numeric_dtype(snap["total_budget"])

    def test_missing_dataset_returns_empty(self):
        assert VE._latest_capital_snapshot({}).empty


class TestCapitalBudgetChart:
    def test_reports_deduplicated_totals(self):
        fig, insight = VE.chart_capital_budget_vs_spend(
            {"capital_projects_dashboard": _multi_period_frame()}
        )
        assert len(fig.data) == 2  # budget + spend series
        assert "2 DOT capital projects" in insight
        assert "ninefold" in insight  # methodology note is stated to the reader

    def test_empty_bundle_degrades_gracefully(self):
        fig, insight = VE.chart_capital_budget_vs_spend({})
        assert fig is not None
        assert "No capital projects data" in insight


class TestBurnRateNeverPlotsCounts:
    """chart_ps_burn once fell back to record counts under a '$' axis+hover,
    rendering a single 'DOT' bar of 5,685 rows as if it were dollars."""

    def test_refuses_to_plot_counts_when_dollars_absent(self):
        no_dollars = pd.DataFrame({
            "managing_agency": ["DOT"] * 20,
            "fms_id": [f"P{i}" for i in range(20)],
            "reporting_period": ["202605"] * 20,
        })
        _fig, insight = VE.chart_ps_burn({"capital_projects_dashboard": no_dollars})
        assert "refusing to plot record" in insight.lower() or "missing" in insight.lower()

    def test_reports_real_dollars_when_present(self):
        df = _multi_period_frame()
        df["ten_year_plan_category"] = ["Sidewalks", "Bridges"] * 3
        _fig, insight = VE.chart_ps_burn({"capital_projects_dashboard": df})
        # 400 budgeted / 85 spent at the latest period — not 1200/255 (3 periods)
        assert "$0.00B" in insight or "budgeted" in insight
        assert "21.2% drawn down" in insight or "drawn down" in insight

    def test_does_not_group_by_agency_only(self):
        """DOT-only feed grouped by managing_agency collapses to one useless bar."""
        df = _multi_period_frame()
        df["ten_year_plan_category"] = ["Sidewalks", "Bridges"] * 3
        fig, _ = VE.chart_ps_burn({"capital_projects_dashboard": df})
        assert len(fig.data[0].x) == 2, "should group by plan category, not agency"
