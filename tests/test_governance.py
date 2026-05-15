import json

import pandas as pd

from socrata_toolkit.governance import (
    AuditLogger,
    LineageRecord,
    apply_retention_policy,
    compute_quality_score,
    create_lineage,
    detect_schema_drift,
    load_schema_snapshot,
    save_schema_snapshot,
    snapshot_schema,
)

# -- Lineage -----------------------------------------------------------------


def test_create_lineage():
    lr = create_lineage("abcd-1234")
    assert lr.dataset_id == "abcd-1234"
    assert len(lr.run_id) == 12
    assert lr.steps == []


def test_lineage_add_step():
    lr = create_lineage("abcd-1234", run_id="test-run")
    lr.add_step("fetch", source="socrata", action="fetch", row_count_in=0, row_count_out=100)
    lr.add_step("filter", source="memory", action="filter", row_count_in=100, row_count_out=80)
    assert len(lr.steps) == 2
    assert lr.steps[0].row_count_out == 100
    assert lr.steps[1].action == "filter"


def test_lineage_save_and_load(tmp_path):
    path = str(tmp_path / "lineage.json")
    lr = create_lineage("test-ds", run_id="run-1")
    lr.add_step("ingest", source="api", action="fetch", row_count_in=0, row_count_out=50)
    lr.save(path)

    loaded = LineageRecord.load(path)
    assert loaded.dataset_id == "test-ds"
    assert loaded.run_id == "run-1"
    assert len(loaded.steps) == 1


def test_lineage_to_dict():
    lr = create_lineage("ds", run_id="r1")
    lr.add_step("s1", source="src", action="fetch", row_count_in=0, row_count_out=10)
    d = lr.to_dict()
    assert d["dataset_id"] == "ds"
    assert len(d["steps"]) == 1


# -- Audit Logger ------------------------------------------------------------


def test_audit_logger_log_and_query():
    logger = AuditLogger()
    logger.log_event("user-a", "read", "dataset-1")
    logger.log_event("user-b", "write", "dataset-2")
    logger.log_event("user-a", "export", "dataset-1")

    assert len(logger.events) == 3
    assert len(logger.query(actor="user-a")) == 2
    assert len(logger.query(action="write")) == 1
    assert len(logger.query(resource="dataset-1")) == 2


def test_audit_logger_flush(tmp_path):
    path = str(tmp_path / "audit.json")
    logger = AuditLogger()
    logger.log_event("u1", "read", "r1")
    logger.log_event("u2", "write", "r2")
    count = logger.flush(path)
    assert count == 2
    assert len(logger.events) == 0

    data = json.loads(open(path).read())
    assert len(data) == 2

    # Flush again: should append
    logger.log_event("u3", "delete", "r3")
    logger.flush(path)
    data = json.loads(open(path).read())
    assert len(data) == 3


# -- Quality Scoring ---------------------------------------------------------


def test_compute_quality_score_full():
    df = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"], "val": [10, 20, 30]})
    score = compute_quality_score(df, key_columns=["id"])
    assert score.completeness == 100.0
    assert score.consistency == 100.0
    assert score.overall > 90


def test_compute_quality_score_with_nulls():
    df = pd.DataFrame({"id": [1, 2, 3], "name": ["a", None, None]})
    score = compute_quality_score(df, key_columns=["id"])
    assert score.completeness < 100.0


def test_compute_quality_score_with_duplicates():
    df = pd.DataFrame({"id": [1, 1, 2], "v": [10, 20, 30]})
    score = compute_quality_score(df, key_columns=["id"])
    assert score.consistency < 100.0


def test_compute_quality_score_with_type_rules():
    df = pd.DataFrame({"count": ["1", "2", "not_a_number"], "name": ["a", "b", "c"]})
    score = compute_quality_score(
        df,
        type_rules={"count": "numeric", "name": "string"},
    )
    # 2 of 3 numeric values valid, 3 of 3 strings valid -> validity < 100
    assert score.validity < 100.0


# -- Schema Drift Detection --------------------------------------------------


def test_detect_schema_drift_no_changes():
    df = pd.DataFrame({"a": [1], "b": ["x"]})
    baseline = snapshot_schema(df)
    diff = detect_schema_drift(df, baseline)
    assert diff.is_compatible is True
    assert diff.added_columns == []
    assert diff.removed_columns == []
    assert diff.type_changes == []


def test_detect_schema_drift_added_column():
    baseline = {"a": "int64"}
    df = pd.DataFrame({"a": [1], "b": ["x"]})
    diff = detect_schema_drift(df, baseline)
    assert "b" in diff.added_columns
    assert diff.is_compatible is True  # additions are compatible


def test_detect_schema_drift_removed_column():
    baseline = {"a": "int64", "b": "object"}
    df = pd.DataFrame({"a": [1]})
    diff = detect_schema_drift(df, baseline)
    assert "b" in diff.removed_columns
    assert diff.is_compatible is False  # removals break compatibility


def test_detect_schema_drift_type_change():
    baseline = {"a": "int64"}
    df = pd.DataFrame({"a": ["text"]})
    diff = detect_schema_drift(df, baseline)
    assert len(diff.type_changes) == 1
    assert diff.is_compatible is False


def test_save_and_load_schema_snapshot(tmp_path):
    path = str(tmp_path / "schema.json")
    df = pd.DataFrame({"id": [1], "name": ["x"]})
    save_schema_snapshot(df, path)
    loaded = load_schema_snapshot(path)
    assert "id" in loaded
    assert "name" in loaded


# -- Retention Policy --------------------------------------------------------


def test_apply_retention_policy():
    df = pd.DataFrame(
        {
            "created": ["2020-01-01", "2024-01-01", "2025-12-01"],
            "val": [1, 2, 3],
        }
    )
    retained, report = apply_retention_policy(df, "created", retention_days=365)
    assert report.total_rows == 3
    assert report.expired_rows >= 1
    assert len(retained) < 3


def test_apply_retention_policy_keeps_unparseable():
    df = pd.DataFrame(
        {
            "created": ["not-a-date", "2025-01-01"],
            "val": [1, 2],
        }
    )
    retained, report = apply_retention_policy(df, "created", retention_days=365)
    # "not-a-date" should be kept (NaT)
    assert len(retained) >= 1
