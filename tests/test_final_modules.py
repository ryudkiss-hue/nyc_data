"""Tests for SLA tracking, notification rules, data dictionary, NYC datasets, sample data."""

import pandas as pd

# -- SLA Tracking -------------------------------------------------------------
from socrata_toolkit.analysis import (
    SLATarget,
    compute_cycle_times,
    compute_sla_metrics,
    flag_sla_violations,
)


def test_compute_cycle_times():
    df = pd.DataFrame(
        {
            "complaint_date": ["2024-01-01", "2024-02-01"],
            "inspection_date": ["2024-01-20", "2024-02-10"],
            "repair_date": ["2024-04-01", "2024-03-15"],
        }
    )
    result = compute_cycle_times(df)
    assert "_days_complaint_to_inspection" in result.columns
    assert "_days_total_cycle" in result.columns
    assert result.loc[0, "_days_complaint_to_inspection"] == 19

def test_compute_sla_metrics():
    df = pd.DataFrame(
        {
            "complaint_date": ["2024-01-01", "2024-02-01"],
            "inspection_date": ["2024-01-20", "2024-02-10"],
            "repair_date": ["2024-04-01", "2024-03-15"],
            "borough": ["MANHATTAN", "BROOKLYN"],
        }
    )
    metrics = compute_sla_metrics(df)
    assert metrics.avg_total_cycle_days > 0
    assert metrics.sla_compliance_rate >= 0

def test_flag_sla_violations():
    df = pd.DataFrame(
        {
            "complaint_date": ["2024-01-01"],
            "inspection_date": ["2024-06-01"],  # 152 days - violation
            "repair_date": ["2024-12-01"],
        }
    )
    result = flag_sla_violations(df, target=SLATarget(complaint_to_inspection_days=30))
    assert bool(result.loc[0, "_sla_violation"]) is True

# -- Notification Rules -------------------------------------------------------

from socrata_toolkit.alerts.rules import Rule, RulesEngine


def test_rules_engine_evaluate():
    engine = RulesEngine()
    engine.add_rule(
        Rule(
            "high_backlog",
            field="pending_count",
            operator=">",
            threshold=100,
            message="Backlog too high",
        )
    )
    alerts = engine.evaluate({"pending_count": 150})
    assert len(alerts) == 1
    assert "Backlog" in alerts[0].message

def test_rules_engine_no_trigger():
    engine = RulesEngine()
    engine.add_rule(Rule("test", field="count", operator=">", threshold=100))
    alerts = engine.evaluate({"count": 50})
    assert len(alerts) == 0

def test_rules_engine_multiple_operators():
    engine = RulesEngine()
    engine.add_rule(Rule("r1", field="cpi", operator="<", threshold=0.9))
    engine.add_rule(Rule("r2", field="score", operator=">=", threshold=80))
    alerts = engine.evaluate({"cpi": 0.7, "score": 85})
    assert len(alerts) == 2

def test_rules_engine_save_and_load(tmp_path):
    path = str(tmp_path / "rules.json")
    engine = RulesEngine()
    engine.add_rule(Rule("r1", field="x", operator=">", threshold=10))
    engine.save(path)
    engine2 = RulesEngine()
    engine2.load(path)
    assert len(engine2.rules) == 1

def test_rules_engine_evaluate_dataframe():
    df = pd.DataFrame(
        {"borough": ["MANHATTAN"] * 5, "status": ["Pending Repair"] * 3 + ["Complete"] * 2}
    )
    engine = RulesEngine()
    engine.add_rule(Rule("pending", field="pending_count", operator=">", threshold=2))
    alerts = engine.evaluate_dataframe(df)
    assert len(alerts) == 1

# -- Data Dictionary ----------------------------------------------------------

from socrata_toolkit.core import generate_data_dictionary


def test_generate_data_dictionary():
    df = pd.DataFrame({"id": [1, 2, 3], "name": ["a", None, "c"], "score": [10.5, 20.3, None]})
    dd = generate_data_dictionary(df, dataset_name="Test Data")
    assert dd.row_count == 3
    assert dd.column_count == 3
    assert len(dd.columns) == 3
    # Check null detection
    name_col = [c for c in dd.columns if c.name == "name"][0]
    assert name_col.null_count == 1

def test_data_dictionary_to_markdown():
    df = pd.DataFrame({"x": [1, 2], "y": ["a", "b"]})
    dd = generate_data_dictionary(df)
    md = dd.to_markdown()
    assert "| `x`" in md
    assert "| `y`" in md

def test_data_dictionary_save(tmp_path):
    df = pd.DataFrame({"x": [1]})
    dd = generate_data_dictionary(df)
    path = dd.save(str(tmp_path / "dd.md"))
    content = open(path).read()
    assert "Data Dictionary" in content

# -- NYC Datasets Registry ----------------------------------------------------

from socrata_toolkit.core import DATASETS, list_available_datasets


def test_datasets_registry():
    assert "311_service_requests" in DATASETS
    assert "sidewalk_violations" in DATASETS
    assert DATASETS["311_service_requests"].fourfour == "erm2-nwe9"

def test_list_available_datasets():
    result = list_available_datasets()
    assert len(result) >= 5
    assert all("key" in d and "fourfour" in d for d in result)

# -- Sample Data Loading ------------------------------------------------------

def test_sample_inspections_loads():
    df = pd.read_csv("data/samples/inspections.csv")
    assert len(df) == 10
    assert "borough" in df.columns
    assert "severity_rating" in df.columns

def test_sample_contracts_loads():
    df = pd.read_csv("data/samples/contracts.csv")
    assert len(df) == 5
    assert "contract_id" in df.columns

def test_sample_complaints_loads():
    df = pd.read_csv("data/samples/complaints_311.csv")
    assert len(df) == 8
    assert "complaint_type" in df.columns
