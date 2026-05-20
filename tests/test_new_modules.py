"""Tests for all new modules: cost estimator, change detection, contractor scorecards,
budget forecast, map view, QGIS, PDF reports, messaging bot, 311 ingestion."""

import pandas as pd

# -- Cost Estimator -----------------------------------------------------------
from socrata_toolkit.engineering import (
    estimate_costs,
    estimate_single,
    summarize_costs,
)


def test_estimate_single():
    est = estimate_single(100, scope="sidewalk_repair", borough="MANHATTAN", ada_required=True)
    assert est.total > 0
    assert est.base_cost == 2500.0  # 100 * 25
    assert est.borough_adjustment > 0  # Manhattan multiplier
    assert est.ada_surcharge > 0


def test_estimate_costs():
    df = pd.DataFrame(
        {
            "estimated_sqft": [100, 200],
            "_scope": ["sidewalk_repair", "pedestrian_ramp"],
            "borough": ["MANHATTAN", "BROOKLYN"],
            "_ada_required": [False, True],
        }
    )
    result = estimate_costs(df)
    assert "_cost_total" in result.columns
    assert result.loc[0, "_cost_total"] > 0
    assert result.loc[1, "_cost_total"] > result.loc[0, "_cost_total"]  # ramp + ADA more expensive


def test_summarize_costs():
    df = pd.DataFrame(
        {
            "estimated_sqft": [100, 200],
            "_scope": ["sidewalk_repair", "pedestrian_ramp"],
            "borough": ["MANHATTAN", "BROOKLYN"],
            "_cost_total": [3000, 8000],
        }
    )
    summary = summarize_costs(df)
    assert summary.total_estimated == 11000
    assert summary.location_count == 2


# -- Change Detection ---------------------------------------------------------

from socrata_toolkit.pipeline import detect_changes, detect_status_changes


def test_detect_changes_added_removed():
    old = pd.DataFrame({"id": [1, 2, 3], "val": ["a", "b", "c"]})
    new = pd.DataFrame({"id": [2, 3, 4], "val": ["b", "C", "d"]})
    changes = detect_changes(old, new, key_col="id")
    assert changes.added_count == 1
    assert changes.removed_count == 1
    assert 4 in changes.added_keys
    assert 1 in changes.removed_keys


def test_detect_changes_modified():
    old = pd.DataFrame({"id": [1, 2], "status": ["Pending", "Complete"]})
    new = pd.DataFrame({"id": [1, 2], "status": ["Complete", "Complete"]})
    changes = detect_changes(old, new, key_col="id")
    assert changes.modified_count == 1
    assert changes.unchanged_count == 1


def test_detect_status_changes():
    old = pd.DataFrame({"id": [1, 2], "status": ["Pending", "In Progress"]})
    new = pd.DataFrame({"id": [1, 2], "status": ["Complete", "In Progress"]})
    result = detect_status_changes(old, new)
    assert len(result) == 1
    assert result.iloc[0]["new_status"] == "Complete"


# -- Contractor Scorecards ----------------------------------------------------

from socrata_toolkit.engineering import (
    generate_scorecards,
    scorecards_to_dataframe,
)


def test_generate_scorecards():
    df = pd.DataFrame(
        {
            "contractor": ["Acme", "Acme", "BestCo"],
            "actual_sqft": [1000, 500, 2000],
            "actual_spend": [25000, 15000, 40000],
            "days_worked": [20, 10, 30],
            "status": ["complete", "complete", "complete"],
        }
    )
    cards = generate_scorecards(df)
    assert len(cards) == 2
    assert cards[0].overall_score >= cards[1].overall_score  # sorted by score


def test_scorecards_to_dataframe():
    df = pd.DataFrame(
        {
            "contractor": ["A"],
            "actual_sqft": [100],
            "actual_spend": [5000],
            "days_worked": [5],
            "status": ["complete"],
        }
    )
    cards = generate_scorecards(df)
    result = scorecards_to_dataframe(cards)
    assert isinstance(result, pd.DataFrame)
    assert "contractor" in result.columns


# -- Budget Forecast ----------------------------------------------------------

from socrata_toolkit.engineering import (
    forecast_completion,
    forecast_spend,
    forecast_workload,
)


def test_forecast_spend():
    dates = pd.date_range("2024-01-01", periods=6, freq="ME")
    df = pd.DataFrame({"date": dates, "actual_spend": [10000, 12000, 11000, 13000, 12500, 14000]})
    fc = forecast_spend(df, horizon_months=3)
    assert fc.current_spend > 0
    assert fc.projected_total > fc.current_spend
    assert len(fc.forecast_values) == 3


def test_forecast_completion():
    df = pd.DataFrame({"remaining_sqft": [5000, 3000]})
    fc = forecast_completion(df, daily_capacity=500)
    assert fc.projected_days == 16  # 8000 / 500
    assert len(fc.weekly_projection) > 0


def test_forecast_workload():
    projection = forecast_workload(100, weekly_intake=50, weekly_completion=40, horizon_weeks=10)
    assert len(projection) == 10
    assert projection[0]["backlog"] == 110  # 100 + 50 - 40


# -- Map View -----------------------------------------------------------------

from socrata_toolkit.analysis import create_map, save_map


def test_create_map_fallback():
    df = pd.DataFrame({"latitude": [40.75], "longitude": [-73.99], "status": ["Pending"]})
    html = create_map(df)
    assert "<" in html  # some HTML generated


def test_save_map(tmp_path):
    html = "<html><body>test map</body></html>"
    path = save_map(html, str(tmp_path / "map.html"))
    assert "map.html" in path


# -- QGIS Integration --------------------------------------------------------

from socrata_toolkit.spatial import generate_qgis_project


def test_generate_qgis_project(tmp_path):
    path = generate_qgis_project(
        "postgresql://user:pass@localhost/sidewalk_db",
        layers=["inspections", "permits"],
        output=str(tmp_path / "project.qgs"),
    )
    content = open(path).read()
    assert "<qgis" in content
    assert "inspections" in content
    assert "permits" in content


# -- PDF Reports --------------------------------------------------------------

from socrata_toolkit.analysis import dataframe_to_pdf


def test_dataframe_to_pdf_fallback(tmp_path):
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    path = dataframe_to_pdf(df, str(tmp_path / "report.pdf"), title="Test Report")
    # Falls back to HTML without weasyprint
    assert path.endswith(".html") or path.endswith(".pdf")
    content = open(path).read()
    assert "Test Report" in content


# -- Messaging Bot -------------------------------------------------------------

from socrata_toolkit.alerts.messaging import BotAdapter


def test_bot_greeting():
    bot = BotAdapter()
    resp = bot.handle("hello")
    assert resp.intent == "greeting"
    assert "DOT" in resp.text


def test_bot_help():
    bot = BotAdapter()
    resp = bot.handle("help")
    assert resp.intent == "help"
    assert "contract" in resp.text.lower()


def test_bot_contract_status():
    df = pd.DataFrame(
        {"contract_id": ["C-1", "C-1", "C-2"], "status": ["Complete", "Pending", "Complete"]}
    )
    bot = BotAdapter(default_data=df)
    resp = bot.handle("status of contract C-1")
    assert resp.intent == "contract_status"
    assert "C-1" in resp.text
    assert resp.data["records"] == 2


def test_bot_borough_backlog():
    df = pd.DataFrame(
        {
            "borough": ["MANHATTAN", "MANHATTAN", "BROOKLYN"],
            "status": ["Pending Repair", "Complete", "Pending Repair"],
        }
    )
    bot = BotAdapter(default_data=df)
    resp = bot.handle("manhattan backlog")
    assert resp.intent == "borough_backlog"
    assert "1 pending" in resp.text


def test_bot_quality_score():
    df = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
    bot = BotAdapter(default_data=df)
    resp = bot.handle("quality score")
    assert resp.intent == "quality_score"
    assert "100" in resp.text  # full completeness


def test_bot_unknown():
    bot = BotAdapter()
    resp = bot.handle("asdf gibberish xyz")
    assert resp.intent == "unknown"


# -- 311 Complaint Ingestion (unit test only, no API call) --------------------

import pandas as pd

from socrata_toolkit.nlp.integration import triage_complaints
from socrata_toolkit.pipeline import IngestionResult


def test_triage_complaints_sets_priority_column():
    df = pd.DataFrame(
        {"descriptor": ["unsafe sidewalk collapse", "cracked sidewalk panel", ""]},
    )
    out = triage_complaints(df, text_col="descriptor")
    assert "_triage_priority" in out.columns
    assert out.loc[0, "_triage_priority"] == "critical"
    assert out.loc[1, "_triage_priority"] == "high"
    assert out.loc[2, "_triage_priority"] == "medium"


def test_nlp_integration_shim_import():
    from socrata_toolkit.nlp_integration import triage_complaints as shim_triage

    assert shim_triage is triage_complaints


def test_ingestion_result_struct():
    result = IngestionResult(
        total=50,
        sidewalk_related=50,
        critical_count=5,
        high_count=10,
        boroughs={"MANHATTAN": 20},
        task_board_items_created=0,
    )
    assert result.total == 50
    assert result.critical_count == 5
