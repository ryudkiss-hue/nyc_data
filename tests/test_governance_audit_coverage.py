"""Tests for governance.audit module - AuditTrail, AuditEvent, _InProcessTrail."""
from __future__ import annotations

import io
import json
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from socrata_toolkit.governance.audit import (
    ActionType,
    AuditEntry,
    AuditEvent,
    AuditTrail,
    ChangeType,
    _InProcessTrail,
    audit_op,
    get_global_trail,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fresh_trail():
    """Return a new _InProcessTrail with no entries."""
    trail = _InProcessTrail(maxlen=100)
    return trail

@pytest.fixture
def sample_audit_event():
    """Return a sample AuditEvent for use in serialisation tests."""
    return AuditEvent(
        audit_id="test-uuid-1234",
        timestamp=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        user_name="analyst@nyc.gov",
        action=ActionType.INSERT.value,
        entity_type="sidewalk_conditions",
        entity_id="sidewalk_123",
        change_type=ChangeType.DATA_CHANGE.value,
        old_values=None,
        new_values={"condition": "good", "width": 5.0},
        diff={"condition": [None, "good"], "width": [None, 5.0]},
        reason="Initial record",
        lineage_node_id="lineage-node-001",
        correlation_id="corr-001",
        ip_address="10.0.0.1",
        user_agent="socrata-toolkit/1.0",
    )

# ---------------------------------------------------------------------------
# _InProcessTrail tests
# ---------------------------------------------------------------------------

class TestInProcessTrail:
    """Tests for _InProcessTrail thread-safe ring buffer."""

    def test_record_returns_entry(self, fresh_trail):
        """Record should return an AuditEntry with expected fields."""
        entry = fresh_trail.record("fetch", detail="fourfour=dntt-gqwq", user="agent")
        assert isinstance(entry, AuditEntry)
        assert entry.operation == "fetch"
        assert entry.detail == "fourfour=dntt-gqwq"
        assert entry.user == "agent"
        assert entry.success is True
        assert entry.error == ""

    def test_record_stores_entry(self, fresh_trail):
        """Recorded entries should appear in entries()."""
        fresh_trail.record("export", detail="csv")
        entries = fresh_trail.entries()
        assert len(entries) == 1
        assert entries[0].operation == "export"

    def test_record_failure_entry(self, fresh_trail):
        """A failed operation should set success=False and populate error."""
        entry = fresh_trail.record("fetch", success=False, error="Connection refused")
        assert entry.success is False
        assert entry.error == "Connection refused"

    def test_record_truncates_detail_at_200_chars(self, fresh_trail):
        """Detail exceeding 200 chars should be truncated."""
        long_detail = "x" * 300
        entry = fresh_trail.record("op", detail=long_detail)
        assert len(entry.detail) == 200

    def test_record_truncates_error_at_200_chars(self, fresh_trail):
        """Error exceeding 200 chars should be truncated."""
        long_error = "e" * 300
        entry = fresh_trail.record("op", success=False, error=long_error)
        assert len(entry.error) == 200

    def test_ring_buffer_evicts_oldest(self):
        """Ring buffer should evict oldest entries when maxlen is exceeded."""
        trail = _InProcessTrail(maxlen=5)
        for i in range(10):
            trail.record(f"op{i}")
        entries = trail.entries()
        assert len(entries) == 5
        assert entries[0].operation == "op5"
        assert entries[-1].operation == "op9"

    def test_entries_returns_copy(self, fresh_trail):
        """entries() should return a copy, not the internal list."""
        fresh_trail.record("op1")
        result = fresh_trail.entries()
        result.clear()
        assert len(fresh_trail.entries()) == 1

    def test_clear_removes_all_entries(self, fresh_trail):
        """clear() should empty the buffer."""
        for _ in range(5):
            fresh_trail.record("op")
        fresh_trail.clear()
        assert fresh_trail.entries() == []

    def test_to_json_returns_valid_json(self, fresh_trail):
        """to_json() should produce valid JSON with expected fields."""
        fresh_trail.record("fetch", detail="test", user="bot")
        result = fresh_trail.to_json()
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["operation"] == "fetch"
        assert parsed[0]["user"] == "bot"
        assert "timestamp" in parsed[0]

    def test_to_json_empty_trail(self, fresh_trail):
        """to_json() on empty trail should return an empty JSON array."""
        result = fresh_trail.to_json()
        assert json.loads(result) == []

    def test_thread_safety_concurrent_writes(self, fresh_trail):
        """Multiple threads writing concurrently should not corrupt the buffer."""
        errors = []

        def writer(n: int) -> None:
            try:
                for _ in range(20):
                    fresh_trail.record(f"op-{n}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert len(fresh_trail.entries()) == 100

    def test_timestamp_is_utc_iso_format(self, fresh_trail):
        """Recorded timestamps should be ISO-8601 UTC strings."""
        entry = fresh_trail.record("op")
        parsed = datetime.fromisoformat(entry.timestamp)
        assert parsed.tzinfo is not None

# ---------------------------------------------------------------------------
# audit_op decorator tests
# ---------------------------------------------------------------------------

class TestAuditOpDecorator:
    """Tests for the audit_op decorator."""

    def test_decorator_records_success(self):
        """Successful calls should create a success=True entry."""
        trail = get_global_trail()
        trail.clear()

        @audit_op("test-op", user="decorator-test")
        def my_fn(x: int) -> int:
            return x * 2

        result = my_fn(5)
        assert result == 10

        entries = trail.entries()
        success_entries = [e for e in entries if e.operation == "test-op"]
        assert len(success_entries) >= 1
        assert success_entries[-1].success is True
        assert success_entries[-1].user == "decorator-test"

    def test_decorator_records_failure_and_reraises(self):
        """Failed calls should create a success=False entry and re-raise the exception."""
        trail = get_global_trail()
        trail.clear()

        @audit_op("fail-op", user="fail-user")
        def bad_fn() -> None:
            raise ValueError("something went wrong")

        with pytest.raises(ValueError, match="something went wrong"):
            bad_fn()

        entries = trail.entries()
        fail_entries = [e for e in entries if e.operation == "fail-op"]
        assert len(fail_entries) >= 1
        assert fail_entries[-1].success is False
        assert "something went wrong" in fail_entries[-1].error

    def test_decorator_preserves_function_metadata(self):
        """audit_op should preserve the wrapped function's __name__ and __doc__."""
        @audit_op("meta-op")
        def documented_fn():
            """This is a docstring."""
            pass

        assert documented_fn.__name__ == "documented_fn"
        assert documented_fn.__doc__ == "This is a docstring."

    def test_decorator_records_kwargs(self):
        """Call detail should reflect presence of kwargs."""
        trail = get_global_trail()
        trail.clear()

        @audit_op("kw-op")
        def fn_with_kwargs(a: int, b: str = "default") -> str:
            return f"{a}-{b}"

        fn_with_kwargs(1, b="custom")
        entries = [e for e in trail.entries() if e.operation == "kw-op"]
        assert len(entries) >= 1
        assert "kwargs=['b']" in entries[-1].detail

# ---------------------------------------------------------------------------
# AuditEvent tests
# ---------------------------------------------------------------------------

class TestAuditEvent:
    """Tests for AuditEvent dataclass."""

    def test_to_dict_roundtrip(self, sample_audit_event):
        """to_dict() should produce a dict that fully describes the event."""
        d = sample_audit_event.to_dict()
        assert d["audit_id"] == "test-uuid-1234"
        assert d["user_name"] == "analyst@nyc.gov"
        assert d["action"] == ActionType.INSERT.value
        assert d["entity_type"] == "sidewalk_conditions"
        assert d["entity_id"] == "sidewalk_123"
        assert d["change_type"] == ChangeType.DATA_CHANGE.value
        assert d["reason"] == "Initial record"
        assert d["lineage_node_id"] == "lineage-node-001"
        assert d["ip_address"] == "10.0.0.1"
        assert isinstance(d["timestamp"], str)
        assert isinstance(d["created_at"], str)

    def test_to_dict_none_optional_fields(self):
        """Optional fields should be None in the output dict when not provided."""
        event = AuditEvent(
            audit_id="x",
            timestamp=datetime.now(timezone.utc),
            user_name="SYSTEM",
            action=ActionType.DELETE.value,
            entity_type="table",
            entity_id="entity-1",
            change_type=ChangeType.DELETE.value,
        )
        d = event.to_dict()
        assert d["old_values"] is None
        assert d["new_values"] is None
        assert d["diff"] is None
        assert d["reason"] is None
        assert d["lineage_node_id"] is None
        assert d["correlation_id"] is None
        assert d["ip_address"] is None
        assert d["user_agent"] is None

    def test_from_dict_creates_event(self, sample_audit_event):
        """from_dict() should reconstruct an AuditEvent from a dict."""
        d = {
            "audit_id": "abc-123",
            "timestamp": datetime.now(timezone.utc),
            "user_name": "analyst",
            "action": ActionType.UPDATE.value,
            "entity_type": "inspection",
            "entity_id": "insp-99",
            "change_type": ChangeType.DATA_CHANGE.value,
            "old_values": {"status": "open"},
            "new_values": {"status": "closed"},
            "diff": {"status": ["open", "closed"]},
            "reason": "closed by system",
        }
        event = AuditEvent.from_dict(d)
        assert event.audit_id == "abc-123"
        assert event.user_name == "analyst"
        assert event.action == ActionType.UPDATE.value
        assert event.old_values == {"status": "open"}
        assert event.new_values == {"status": "closed"}

    def test_default_created_at_is_utc(self):
        """created_at should default to a UTC-aware datetime."""
        event = AuditEvent(
            audit_id="z",
            timestamp=datetime.now(timezone.utc),
            user_name="SYSTEM",
            action=ActionType.INSERT.value,
            entity_type="tbl",
            entity_id="row-1",
            change_type=ChangeType.DATA_CHANGE.value,
        )
        assert event.created_at.tzinfo is not None

    def test_prov_type_default(self):
        """prov_type should default to 'prov:Activity'."""
        event = AuditEvent(
            audit_id="z",
            timestamp=datetime.now(timezone.utc),
            user_name="SYSTEM",
            action=ActionType.INSERT.value,
            entity_type="tbl",
            entity_id="row-1",
            change_type=ChangeType.DATA_CHANGE.value,
        )
        assert event.prov_type == "prov:Activity"

# ---------------------------------------------------------------------------
# AuditTrail._calculate_diff tests
# ---------------------------------------------------------------------------

class TestCalculateDiff:
    """Tests for the static _calculate_diff method."""

    def test_diff_detects_changed_field(self):
        """Fields with different values should appear in the diff."""
        old = {"status": "open", "severity": 3}
        new = {"status": "closed", "severity": 3}
        diff = AuditTrail._calculate_diff(old, new)
        assert "status" in diff
        assert diff["status"] == ["open", "closed"]
        assert "severity" not in diff

    def test_diff_detects_added_field(self):
        """Fields present only in new should appear in the diff with old=None."""
        old = {"a": 1}
        new = {"a": 1, "b": 2}
        diff = AuditTrail._calculate_diff(old, new)
        assert "b" in diff
        assert diff["b"] == [None, 2]

    def test_diff_detects_removed_field(self):
        """Fields present only in old should appear in the diff with new=None."""
        old = {"a": 1, "b": 2}
        new = {"a": 1}
        diff = AuditTrail._calculate_diff(old, new)
        assert "b" in diff
        assert diff["b"] == [2, None]

    def test_diff_returns_empty_for_no_changes(self):
        """No changes should produce an empty diff."""
        old = {"x": 10, "y": "abc"}
        new = {"x": 10, "y": "abc"}
        diff = AuditTrail._calculate_diff(old, new)
        assert diff == {}

    def test_diff_handles_none_old(self):
        """When old is None it should be treated as empty dict."""
        diff = AuditTrail._calculate_diff(None, {"a": 1})
        assert diff["a"] == [None, 1]

    def test_diff_handles_none_new(self):
        """When new is None it should be treated as empty dict."""
        diff = AuditTrail._calculate_diff({"a": 1}, None)
        assert diff["a"] == [1, None]

    def test_diff_handles_both_none(self):
        """Both None should produce an empty diff."""
        diff = AuditTrail._calculate_diff(None, None)
        assert diff == {}

# ---------------------------------------------------------------------------
# AuditTrail DB tests (mocked psycopg)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_psycopg():
    """Patch psycopg in the audit module so no real DB connection is made."""
    with patch("socrata_toolkit.governance.audit.psycopg") as mock_pg:
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_cur.__enter__ = MagicMock(return_value=mock_cur)
        mock_cur.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cur
        mock_pg.connect.return_value = mock_conn
        yield mock_pg, mock_conn, mock_cur

class TestAuditTrailInit:
    """Tests for AuditTrail initialisation."""

    def test_init_raises_when_psycopg_missing(self):
        """AuditTrail should raise ImportError when psycopg is not installed."""
        with patch("socrata_toolkit.governance.audit.psycopg", None):
            with pytest.raises(ImportError, match="postgres"):
                AuditTrail("postgresql://user:pass@localhost/db")

    def test_init_stores_dsn(self, mock_psycopg):
        """AuditTrail should store the provided DSN."""
        trail = AuditTrail("postgresql://localhost/test")
        assert trail.dsn == "postgresql://localhost/test"

class TestAuditTrailLogInsert:
    """Tests for AuditTrail.log_insert."""

    def test_log_insert_returns_uuid_string(self, mock_psycopg):
        """log_insert should return a non-empty audit_id string."""
        mock_pg, mock_conn, mock_cur = mock_psycopg
        trail = AuditTrail("postgresql://localhost/test")
        audit_id = trail.log_insert(
            table="inspections",
            entity_id="insp-001",
            new_values={"status": "open", "borough": "MN"},
            user="analyst@nyc.gov",
        )
        assert isinstance(audit_id, str)
        assert len(audit_id) > 0

    def test_log_insert_executes_sql(self, mock_psycopg):
        """log_insert should call cursor.execute with INSERT SQL."""
        mock_pg, mock_conn, mock_cur = mock_psycopg
        trail = AuditTrail("postgresql://localhost/test")
        trail.log_insert(
            table="inspections",
            entity_id="insp-002",
            new_values={"status": "closed"},
        )
        mock_cur.execute.assert_called_once()
        sql_call = mock_cur.execute.call_args[0][0]
        assert "INSERT INTO public.audit_trail" in sql_call

    def test_log_insert_commits(self, mock_psycopg):
        """log_insert should commit the transaction."""
        mock_pg, mock_conn, mock_cur = mock_psycopg
        trail = AuditTrail("postgresql://localhost/test")
        trail.log_insert("tbl", "e1", {"a": 1})
        mock_conn.commit.assert_called_once()

    def test_log_insert_sets_action_type(self, mock_psycopg):
        """log_insert should pass ActionType.INSERT as the action parameter."""
        mock_pg, mock_conn, mock_cur = mock_psycopg
        trail = AuditTrail("postgresql://localhost/test")
        trail.log_insert("tbl", "e1", {"a": 1})
        params = mock_cur.execute.call_args[0][1]
        assert ActionType.INSERT.value in params

class TestAuditTrailLogUpdate:
    """Tests for AuditTrail.log_update."""

    def test_log_update_returns_uuid_string(self, mock_psycopg):
        """log_update should return a non-empty audit_id string."""
        mock_pg, mock_conn, mock_cur = mock_psycopg
        trail = AuditTrail("postgresql://localhost/test")
        audit_id = trail.log_update(
            table="sidewalk_conditions",
            entity_id="sw-100",
            old={"condition": "fair"},
            new={"condition": "excellent"},
            user="inspector@nyc.gov",
            reason="Monthly inspection",
        )
        assert isinstance(audit_id, str)
        assert len(audit_id) > 0

    def test_log_update_includes_diff_in_params(self, mock_psycopg):
        """log_update should compute and pass a diff JSON string."""
        mock_pg, mock_conn, mock_cur = mock_psycopg
        trail = AuditTrail("postgresql://localhost/test")
        trail.log_update(
            table="tbl",
            entity_id="e1",
            old={"status": "open"},
            new={"status": "closed"},
        )
        params = mock_cur.execute.call_args[0][1]
        diff_json = params[9]
        diff = json.loads(diff_json)
        assert "status" in diff
        assert diff["status"] == ["open", "closed"]

    def test_log_update_sets_action_type(self, mock_psycopg):
        """log_update should pass ActionType.UPDATE as the action parameter."""
        mock_pg, mock_conn, mock_cur = mock_psycopg
        trail = AuditTrail("postgresql://localhost/test")
        trail.log_update("tbl", "e1", {"x": 1}, {"x": 2})
        params = mock_cur.execute.call_args[0][1]
        assert ActionType.UPDATE.value in params

class TestAuditTrailLogDelete:
    """Tests for AuditTrail.log_delete."""

    def test_log_delete_returns_uuid_string(self, mock_psycopg):
        """log_delete should return a non-empty audit_id string."""
        mock_pg, mock_conn, mock_cur = mock_psycopg
        trail = AuditTrail("postgresql://localhost/test")
        audit_id = trail.log_delete(
            table="violations",
            entity_id="viol-999",
            old_values={"status": "open", "borough": "BK"},
            user="admin@nyc.gov",
        )
        assert isinstance(audit_id, str)

    def test_log_delete_sets_action_and_change_type(self, mock_psycopg):
        """log_delete should set ActionType.DELETE and ChangeType.DELETE."""
        mock_pg, mock_conn, mock_cur = mock_psycopg
        trail = AuditTrail("postgresql://localhost/test")
        trail.log_delete("tbl", "e1", {"a": 1})
        params = mock_cur.execute.call_args[0][1]
        assert ActionType.DELETE.value in params
        assert ChangeType.DELETE.value in params

    def test_log_delete_new_values_is_none_in_params(self, mock_psycopg):
        """log_delete should pass None for new_values in the SQL params."""
        mock_pg, mock_conn, mock_cur = mock_psycopg
        trail = AuditTrail("postgresql://localhost/test")
        trail.log_delete("tbl", "e1", {"a": 1})
        params = mock_cur.execute.call_args[0][1]
        assert params[8] is None

class TestAuditTrailGetEvents:
    """Tests for AuditTrail.get_events."""

    def _make_row(self) -> tuple:
        now = datetime.now(timezone.utc)
        return (
            "audit-id-1",
            now,
            "user1",
            ActionType.UPDATE.value,
            "inspection",
            "insp-001",
            ChangeType.DATA_CHANGE.value,
            json.dumps({"status": "open"}),
            json.dumps({"status": "closed"}),
            json.dumps({"status": ["open", "closed"]}),
            "reason text",
            "lineage-1",
            "corr-1",
            "10.0.0.1",
            "browser/1.0",
            now,
        )

    def test_get_events_returns_list_of_audit_events(self, mock_psycopg):
        """get_events should return a list of AuditEvent objects."""
        mock_pg, mock_conn, mock_cur = mock_psycopg
        mock_cur.fetchall.return_value = [self._make_row()]
        trail = AuditTrail("postgresql://localhost/test")
        events = trail.get_events("inspection", "insp-001")
        assert len(events) == 1
        assert isinstance(events[0], AuditEvent)
        assert events[0].entity_type == "inspection"
        assert events[0].entity_id == "insp-001"

    def test_get_events_decodes_json_fields(self, mock_psycopg):
        """get_events should deserialise old_values, new_values, diff from JSON."""
        mock_pg, mock_conn, mock_cur = mock_psycopg
        mock_cur.fetchall.return_value = [self._make_row()]
        trail = AuditTrail("postgresql://localhost/test")
        events = trail.get_events("inspection", "insp-001")
        assert events[0].old_values == {"status": "open"}
        assert events[0].new_values == {"status": "closed"}
        assert events[0].diff == {"status": ["open", "closed"]}

    def test_get_events_empty_result(self, mock_psycopg):
        """get_events should return an empty list when no rows are found."""
        mock_pg, mock_conn, mock_cur = mock_psycopg
        mock_cur.fetchall.return_value = []
        trail = AuditTrail("postgresql://localhost/test")
        events = trail.get_events("nonexistent_table", "no-entity")
        assert events == []

class TestAuditTrailExportCsv:
    """Tests for AuditTrail.export_csv."""

    def _minimal_event(self) -> AuditEvent:
        return AuditEvent(
            audit_id="csv-1",
            timestamp=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            user_name="exporter",
            action=ActionType.INSERT.value,
            entity_type="inspection",
            entity_id="insp-csv",
            change_type=ChangeType.DATA_CHANGE.value,
            reason="csv export test",
        )

    def test_export_csv_writes_header_and_row(self, mock_psycopg):
        """export_csv should write a CSV with the expected header and one data row."""
        mock_pg, mock_conn, mock_cur = mock_psycopg
        mock_cur.fetchall.return_value = [
            (
                "csv-1",
                datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                "exporter",
                ActionType.INSERT.value,
                "inspection",
                "insp-csv",
                ChangeType.DATA_CHANGE.value,
                "csv export test",
            )
        ]
        trail = AuditTrail("postgresql://localhost/test")
        buf = io.StringIO()
        count = trail.export_csv(buf)
        assert count == 1
        buf.seek(0)
        content = buf.read()
        assert "audit_id" in content
        assert "csv-1" in content

    def test_export_csv_with_criteria_uses_search(self, mock_psycopg):
        """export_csv with criteria should delegate to search_events."""
        mock_pg, mock_conn, mock_cur = mock_psycopg
        mock_cur.fetchall.return_value = []
        trail = AuditTrail("postgresql://localhost/test")
        buf = io.StringIO()
        trail.export_csv(buf, criteria={"entity_type": "inspection"})
        buf.seek(0)
        content = buf.read()
        assert "audit_id" in content

class TestAuditTrailExportJson:
    """Tests for AuditTrail.export_json."""

    def test_export_json_returns_list_of_dicts(self, mock_psycopg):
        """export_json should return a list of serialisable dicts."""
        mock_pg, mock_conn, mock_cur = mock_psycopg
        now = datetime.now(timezone.utc)
        mock_cur.fetchall.return_value = [
            (
                "json-1",
                now,
                "user1",
                ActionType.UPDATE.value,
                "violations",
                "viol-001",
                ChangeType.DATA_CHANGE.value,
                json.dumps({"status": "open"}),
                json.dumps({"status": "closed"}),
                json.dumps({}),
                None,
                None,
                None,
                None,
                None,
                now,
            )
        ]
        trail = AuditTrail("postgresql://localhost/test")
        result = trail.export_json()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["audit_id"] == "json-1"

    def test_export_json_empty_result(self, mock_psycopg):
        """export_json should return an empty list when there are no events."""
        mock_pg, mock_conn, mock_cur = mock_psycopg
        mock_cur.fetchall.return_value = []
        trail = AuditTrail("postgresql://localhost/test")
        result = trail.export_json()
        assert result == []

class TestAuditTrailGenerateComplianceReport:
    """Tests for AuditTrail.generate_compliance_report."""

    def test_compliance_report_structure(self, mock_psycopg):
        """generate_compliance_report should return a dict with all required keys."""
        mock_pg, mock_conn, mock_cur = mock_psycopg
        now = datetime.now(timezone.utc)
        mock_cur.fetchone.side_effect = [
            (42,),
            (now, now),
            (7,),
            (3,),
        ]
        mock_cur.fetchall.side_effect = [
            [("INSERT", 20), ("UPDATE", 15), ("DELETE", 7)],
            [("analyst@nyc.gov",), ("system",)],
        ]
        trail = AuditTrail("postgresql://localhost/test")
        report = trail.generate_compliance_report()
        assert "total_events" in report
        assert "date_range" in report
        assert "actions" in report
        assert "users" in report
        assert "user_count" in report
        assert "unique_entities" in report
        assert "unique_entity_types" in report
        assert "events_per_day" in report

    def test_compliance_report_total_events(self, mock_psycopg):
        """generate_compliance_report should report correct total_events."""
        mock_pg, mock_conn, mock_cur = mock_psycopg
        now = datetime.now(timezone.utc)
        past = datetime(2025, 1, 1, tzinfo=timezone.utc)
        mock_cur.fetchone.side_effect = [
            (100,),
            (past, now),
            (50,),
            (5,),
        ]
        mock_cur.fetchall.side_effect = [
            [("INSERT", 60), ("UPDATE", 40)],
            [("user1",), ("user2",)],
        ]
        trail = AuditTrail("postgresql://localhost/test")
        report = trail.generate_compliance_report()
        assert report["total_events"] == 100
        assert report["user_count"] == 2

# ---------------------------------------------------------------------------
# ActionType and ChangeType enum tests
# ---------------------------------------------------------------------------

class TestEnums:
    """Tests for ActionType and ChangeType enums."""

    def test_action_type_values(self):
        """ActionType enum should have all expected values."""
        expected = {"INSERT", "UPDATE", "DELETE", "TRUNCATE", "SCHEMA_CHANGE"}
        actual = {m.value for m in ActionType}
        assert expected == actual

    def test_change_type_values(self):
        """ChangeType enum should have all expected values."""
        expected = {"DATA_CHANGE", "SCHEMA_CHANGE", "ACCESS", "DELETE", "RESTORE"}
        actual = {m.value for m in ChangeType}
        assert expected == actual

    def test_action_type_is_str_comparable(self):
        """ActionType.value should be directly comparable to string literals."""
        assert ActionType.INSERT.value == "INSERT"
        assert ActionType.UPDATE.value == "UPDATE"
        assert ActionType.DELETE.value == "DELETE"

# ---------------------------------------------------------------------------
# get_global_trail singleton tests
# ---------------------------------------------------------------------------

class TestGetGlobalTrail:
    """Tests for the get_global_trail() singleton accessor."""

    def test_returns_in_process_trail(self):
        """get_global_trail should return an _InProcessTrail instance."""
        trail = get_global_trail()
        assert isinstance(trail, _InProcessTrail)

    def test_returns_same_instance_each_call(self):
        """get_global_trail should return the same object on repeated calls."""
        t1 = get_global_trail()
        t2 = get_global_trail()
        assert t1 is t2
