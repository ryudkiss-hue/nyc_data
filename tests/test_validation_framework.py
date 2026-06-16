"""Comprehensive tests for the enhanced validation framework with audit logging.

Tests cover:
- AuditLogger functionality (logging, JSON export, DuckDB persistence)
- Validation functions with audit integration
- Edge cases and error handling
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import pytest

from socrata_toolkit.governance.audit_logger import AuditEntry, AuditLogger
from socrata_toolkit.quality.duckdb_validation import (
    validate_business_rules,
    validate_counts,
    validate_freshness,
    validate_uniqueness,
)


@pytest.fixture
def audit_logger():
    """Create a fresh audit logger instance."""
    return AuditLogger()


@pytest.fixture
def duckdb_conn():
    """Create an in-memory DuckDB connection for testing."""
    return duckdb.connect(":memory:")


@pytest.fixture
def sample_inspection_table(duckdb_conn):
    """Create a sample inspection table with valid data."""
    duckdb_conn.execute("CREATE SCHEMA IF NOT EXISTS staging")
    duckdb_conn.execute("""
        CREATE TABLE staging.inspections (
            objectid INTEGER PRIMARY KEY,
            condition_score INTEGER,
            violation_count INTEGER,
            inspection_date DATE,
            staged_at TIMESTAMP
        )
    """)

    duckdb_conn.execute("""
        INSERT INTO staging.inspections VALUES
        (1, 85, 2, '2026-05-01', '2026-06-05 10:00:00'),
        (2, 90, 0, '2026-05-02', '2026-06-05 11:00:00'),
        (3, 75, 5, '2026-05-03', '2026-06-05 12:00:00')
    """)

    return duckdb_conn


@pytest.fixture
def sample_raw_table(duckdb_conn):
    """Create sample raw and staging tables for count validation."""
    duckdb_conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
    duckdb_conn.execute("CREATE SCHEMA IF NOT EXISTS staging")
    duckdb_conn.execute("""
        CREATE TABLE raw.inspection (
            id INTEGER,
            data VARCHAR
        )
    """)

    duckdb_conn.execute("""
        CREATE TABLE staging.inspections_clean (
            id INTEGER,
            data VARCHAR
        )
    """)

    # Insert 100 rows in raw table
    for i in range(100):
        duckdb_conn.execute("INSERT INTO raw.inspection VALUES (?, ?)", [i, f"data_{i}"])

    # Insert 97 rows in staging (simulating 3% loss)
    for i in range(97):
        duckdb_conn.execute("INSERT INTO staging.inspections_clean VALUES (?, ?)", [i, f"data_{i}"])

    return duckdb_conn


class TestAuditLoggerBasics:
    """Test basic AuditLogger functionality."""

    def test_audit_logger_initialization(self):
        """Test that AuditLogger initializes with a run_id."""
        logger = AuditLogger()
        assert logger.run_id is not None
        assert len(logger.run_id) > 0
        assert isinstance(logger.entries, list)
        assert len(logger.entries) == 0

    def test_audit_logger_with_provided_run_id(self):
        """Test AuditLogger initialization with provided run_id."""
        custom_run_id = "test_run_123"
        logger = AuditLogger(run_id=custom_run_id)
        assert logger.run_id == custom_run_id

    def test_log_check_creates_entry(self, audit_logger):
        """Test that log_check creates an audit entry."""
        entry = audit_logger.log_check(
            check_type="validate_uniqueness",
            table_name="test_table",
            status="success",
            rows_affected=5,
            details={"duplicate_rows": 0},
        )

        assert isinstance(entry, AuditEntry)
        assert entry.check_type == "validate_uniqueness"
        assert entry.table_name == "test_table"
        assert entry.status == "success"
        assert entry.rows_affected == 5
        assert entry.run_id == audit_logger.run_id
        assert len(audit_logger.entries) == 1

    def test_log_check_with_no_details(self, audit_logger):
        """Test log_check with None details."""
        entry = audit_logger.log_check(
            check_type="validate_freshness", table_name="permits", status="warning"
        )

        assert entry.details == {}
        assert entry.rows_affected == 0

    def test_multiple_log_checks(self, audit_logger):
        """Test logging multiple checks."""
        for i in range(5):
            audit_logger.log_check(
                check_type="validate_counts",
                table_name=f"table_{i}",
                status="success",
                rows_affected=100 + i,
            )

        assert len(audit_logger.entries) == 5
        assert all(entry.check_type == "validate_counts" for entry in audit_logger.entries)


class TestAuditLoggerJsonExport:
    """Test JSON export functionality."""

    def test_audit_to_json_empty_logger(self, audit_logger):
        """Test JSON export of empty audit logger."""
        json_str = audit_logger.to_json()
        data = json.loads(json_str)
        assert isinstance(data, list)
        assert len(data) == 0

    def test_audit_to_json_with_entries(self, audit_logger):
        """Test JSON export with audit entries."""
        audit_logger.log_check(
            check_type="validate_uniqueness",
            table_name="test_table",
            status="success",
            rows_affected=5,
            details={"duplicate_rows": 0},
        )

        audit_logger.log_check(
            check_type="validate_freshness",
            table_name="test_table",
            status="warning",
            rows_affected=0,
            details={"age_hours": 48},
        )

        json_str = audit_logger.to_json()
        data = json.loads(json_str)

        assert len(data) == 2
        assert data[0]["check_type"] == "validate_uniqueness"
        assert data[1]["check_type"] == "validate_freshness"
        assert data[0]["status"] == "success"
        assert data[1]["status"] == "warning"

    def test_audit_to_dict_list(self, audit_logger):
        """Test to_dict_list method."""
        audit_logger.log_check(
            check_type="validate_counts",
            table_name="test_table",
            status="success",
            rows_affected=100,
        )

        dict_list = audit_logger.to_dict_list()

        assert isinstance(dict_list, list)
        assert len(dict_list) == 1
        assert isinstance(dict_list[0], dict)
        assert dict_list[0]["check_type"] == "validate_counts"


class TestAuditLoggerDuckDBPersistence:
    """Test DuckDB persistence functionality."""

    def test_save_to_duckdb_creates_table(self, audit_logger, duckdb_conn):
        """Test that save_to_duckdb creates the audit table."""
        audit_logger.log_check(
            check_type="validate_uniqueness",
            table_name="test_table",
            status="success",
            rows_affected=5,
            details={"duplicate_rows": 0},
        )

        result = audit_logger.save_to_duckdb(duckdb_conn)
        assert result is True

        # Verify table exists
        tables = duckdb_conn.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_name = 'audit_logs'
        """).fetchall()
        assert len(tables) == 1

    def test_save_to_duckdb_inserts_data(self, audit_logger, duckdb_conn):
        """Test that save_to_duckdb persists audit entries."""
        audit_logger.log_check(
            check_type="validate_uniqueness",
            table_name="test_table",
            status="success",
            rows_affected=5,
            details={"duplicate_rows": 0},
        )

        audit_logger.save_to_duckdb(duckdb_conn)

        # Query the audit table
        result = duckdb_conn.execute("""
            SELECT check_type, table_name, status, rows_affected
            FROM audit_logs
        """).fetchall()

        assert len(result) == 1
        assert result[0][0] == "validate_uniqueness"
        assert result[0][1] == "test_table"
        assert result[0][2] == "success"
        assert result[0][3] == 5

    def test_save_to_duckdb_with_multiple_entries(self, audit_logger, duckdb_conn):
        """Test saving multiple audit entries."""
        for i in range(3):
            audit_logger.log_check(
                check_type="validate_counts",
                table_name=f"table_{i}",
                status="success" if i < 2 else "failure",
                rows_affected=100 + i,
            )

        audit_logger.save_to_duckdb(duckdb_conn)

        result = duckdb_conn.execute("""
            SELECT COUNT(*) FROM audit_logs
        """).fetchone()[0]

        assert result == 3

    def test_save_to_duckdb_empty_logger_returns_false(self, audit_logger, duckdb_conn):
        """Test that saving empty audit logger returns False."""
        result = audit_logger.save_to_duckdb(duckdb_conn)
        assert result is False

    def test_save_to_duckdb_with_custom_table_name(self, audit_logger, duckdb_conn):
        """Test saving to custom table name."""
        audit_logger.log_check(
            check_type="validate_uniqueness",
            table_name="test_table",
            status="success",
            rows_affected=5,
        )

        result = audit_logger.save_to_duckdb(duckdb_conn, audit_table="custom_audit")
        assert result is True

        # Verify custom table exists
        tables = duckdb_conn.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_name = 'custom_audit'
        """).fetchall()
        assert len(tables) == 1


class TestValidationWithAuditLogging:
    """Test validation functions with audit logging integration."""

    def test_validate_counts_logs_success(self, audit_logger, sample_raw_table):
        """Test that validate_counts logs a success check."""
        result = validate_counts(
            sample_raw_table,
            "raw.inspection",
            "staging.inspections_clean",
            audit_logger=audit_logger,
        )

        assert result["status"] == "success"
        assert len(audit_logger.entries) == 1

        entry = audit_logger.entries[0]
        assert entry.check_type == "validate_counts"
        assert entry.table_name == "staging.inspections_clean"
        assert entry.status == "success"
        assert entry.details["loss_pct"] == 3.0

    def test_validate_counts_logs_failure(self, audit_logger, duckdb_conn):
        """Test that validate_counts logs a failure when loss exceeds threshold."""
        # Create tables with > 5% loss
        duckdb_conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
        duckdb_conn.execute("CREATE SCHEMA IF NOT EXISTS staging")
        duckdb_conn.execute("CREATE TABLE raw.test (id INTEGER)")
        duckdb_conn.execute("CREATE TABLE staging.test (id INTEGER)")

        for i in range(100):
            duckdb_conn.execute("INSERT INTO raw.test VALUES (?)", [i])

        # Insert only 90 rows (10% loss)
        for i in range(90):
            duckdb_conn.execute("INSERT INTO staging.test VALUES (?)", [i])

        result = validate_counts(duckdb_conn, "raw.test", "staging.test", audit_logger=audit_logger)

        assert result["valid"] is False
        assert len(audit_logger.entries) == 1
        entry = audit_logger.entries[0]
        assert entry.status == "failure"

    def test_validate_counts_logs_error(self, audit_logger, duckdb_conn):
        """Test that validate_counts logs an error when table doesn't exist."""
        result = validate_counts(
            duckdb_conn, "nonexistent_raw", "nonexistent_staging", audit_logger=audit_logger
        )

        assert result["status"] == "error"
        assert len(audit_logger.entries) == 1
        entry = audit_logger.entries[0]
        assert entry.status == "error"

    def test_validate_freshness_logs_check(self, audit_logger, sample_inspection_table):
        """Test that validate_freshness logs a check."""
        result = validate_freshness(
            sample_inspection_table, "staging.inspections", sla_hours=24, audit_logger=audit_logger
        )

        assert len(audit_logger.entries) == 1
        entry = audit_logger.entries[0]
        assert entry.check_type == "validate_freshness"
        assert entry.table_name == "staging.inspections"
        assert entry.status in ["success", "warning"]

    def test_validate_uniqueness_logs_success(self, audit_logger, sample_inspection_table):
        """Test that validate_uniqueness logs a success check."""
        result = validate_uniqueness(
            sample_inspection_table,
            "staging.inspections",
            key_columns=["objectid"],
            audit_logger=audit_logger,
        )

        assert result["valid"] is True
        assert len(audit_logger.entries) == 1
        entry = audit_logger.entries[0]
        assert entry.check_type == "validate_uniqueness"
        assert entry.status == "success"

    def test_validate_uniqueness_logs_duplicates(self, audit_logger, duckdb_conn):
        """Test that validate_uniqueness logs when duplicates are found."""
        duckdb_conn.execute("CREATE SCHEMA IF NOT EXISTS test")
        duckdb_conn.execute("""
            CREATE TABLE test.dups (
                id INTEGER,
                name VARCHAR
            )
        """)

        duckdb_conn.execute("""
            INSERT INTO test.dups VALUES
            (1, 'Alice'),
            (1, 'Alice'),
            (2, 'Bob')
        """)

        result = validate_uniqueness(
            duckdb_conn, "test.dups", key_columns=["id"], audit_logger=audit_logger
        )

        assert result["valid"] is False
        assert result["duplicate_rows"] > 0
        assert len(audit_logger.entries) == 1
        entry = audit_logger.entries[0]
        assert entry.status == "failure"
        assert entry.rows_affected > 0

    def test_validate_business_rules_logs_success(self, audit_logger, sample_inspection_table):
        """Test that validate_business_rules logs a success check."""
        result = validate_business_rules(
            sample_inspection_table, "staging.inspections", audit_logger=audit_logger
        )

        assert result["status"] == "success"
        assert len(audit_logger.entries) == 1
        entry = audit_logger.entries[0]
        assert entry.check_type == "validate_business_rules"
        assert entry.status == "success"

    def test_validate_business_rules_logs_violations(self, audit_logger, duckdb_conn):
        """Test that validate_business_rules logs violations."""
        duckdb_conn.execute("CREATE SCHEMA IF NOT EXISTS test")
        duckdb_conn.execute("""
            CREATE TABLE test.bad_data (
                objectid INTEGER,
                condition_score INTEGER,
                violation_count INTEGER,
                inspection_date DATE
            )
        """)

        # Insert bad data
        duckdb_conn.execute("""
            INSERT INTO test.bad_data VALUES
            (1, 150, 2, '2026-05-01'),
            (2, 85, -5, '2026-06-15')
        """)

        result = validate_business_rules(duckdb_conn, "test.bad_data", audit_logger=audit_logger)

        assert result["valid"] is False
        assert len(audit_logger.entries) == 1
        entry = audit_logger.entries[0]
        assert entry.status == "failure"


class TestAuditLoggerSummary:
    """Test audit logger summary and filtering methods."""

    def test_get_summary_empty(self, audit_logger):
        """Test get_summary on empty logger."""
        summary = audit_logger.get_summary()

        assert summary["run_id"] == audit_logger.run_id
        assert summary["total_entries"] == 0
        assert summary["total_rows_affected"] == 0
        assert summary["timestamp_range"]["start"] is None
        assert summary["timestamp_range"]["end"] is None

    def test_get_summary_with_entries(self, audit_logger):
        """Test get_summary with multiple entries."""
        audit_logger.log_check("check_1", "table_1", "success", 10)
        audit_logger.log_check("check_1", "table_2", "failure", 5)
        audit_logger.log_check("check_2", "table_3", "success", 20)

        summary = audit_logger.get_summary()

        assert summary["total_entries"] == 3
        assert summary["total_rows_affected"] == 35
        assert summary["status_counts"]["success"] == 2
        assert summary["status_counts"]["failure"] == 1
        assert summary["check_type_counts"]["check_1"] == 2
        assert summary["check_type_counts"]["check_2"] == 1

    def test_filter_by_status(self, audit_logger):
        """Test filtering entries by status."""
        audit_logger.log_check("check", "table_1", "success", 10)
        audit_logger.log_check("check", "table_2", "failure", 5)
        audit_logger.log_check("check", "table_3", "success", 20)

        success_entries = audit_logger.filter_by_status("success")
        assert len(success_entries) == 2
        assert all(e.status == "success" for e in success_entries)

        failure_entries = audit_logger.filter_by_status("failure")
        assert len(failure_entries) == 1

    def test_filter_by_check_type(self, audit_logger):
        """Test filtering entries by check type."""
        audit_logger.log_check("validate_counts", "table_1", "success", 10)
        audit_logger.log_check("validate_freshness", "table_2", "success", 5)
        audit_logger.log_check("validate_counts", "table_3", "success", 20)

        count_checks = audit_logger.filter_by_check_type("validate_counts")
        assert len(count_checks) == 2
        assert all(e.check_type == "validate_counts" for e in count_checks)

    def test_filter_by_table(self, audit_logger):
        """Test filtering entries by table name."""
        audit_logger.log_check("check_1", "inspections", "success", 10)
        audit_logger.log_check("check_2", "permits", "success", 5)
        audit_logger.log_check("check_3", "inspections", "failure", 20)

        inspection_entries = audit_logger.filter_by_table("inspections")
        assert len(inspection_entries) == 2
        assert all(e.table_name == "inspections" for e in inspection_entries)


class TestAuditLoggerEdgeCases:
    """Test edge cases and error handling."""

    def test_audit_entry_unique_ids(self, audit_logger):
        """Test that each audit entry has a unique audit_id."""
        audit_logger.log_check("check", "table_1", "success")
        audit_logger.log_check("check", "table_2", "success")

        ids = [entry.audit_id for entry in audit_logger.entries]
        assert len(ids) == len(set(ids))

    def test_validation_without_audit_logger(self, sample_inspection_table):
        """Test that validation functions work without audit logger."""
        result = validate_uniqueness(
            sample_inspection_table, "staging.inspections", key_columns=["objectid"]
        )

        assert result["status"] == "success"
        assert result["valid"] is True

    def test_audit_logger_persistence_with_json_details(self, audit_logger, duckdb_conn):
        """Test that complex details are properly persisted."""
        audit_logger.log_check(
            check_type="complex_check",
            table_name="test",
            status="success",
            rows_affected=10,
            details={"nested": {"key": "value"}, "list": [1, 2, 3], "string": "test"},
        )

        audit_logger.save_to_duckdb(duckdb_conn)

        result = duckdb_conn.execute("""
            SELECT details FROM audit_logs LIMIT 1
        """).fetchone()[0]

        details = json.loads(result)
        assert details["nested"]["key"] == "value"
        assert details["list"] == [1, 2, 3]

    def test_timestamp_format(self, audit_logger):
        """Test that timestamps are in ISO 8601 format with Z suffix."""
        audit_logger.log_check("check", "table", "success")

        entry = audit_logger.entries[0]
        assert entry.timestamp.endswith("Z")
        # Verify it can be parsed as ISO format
        datetime.fromisoformat(entry.timestamp.rstrip("Z"))
