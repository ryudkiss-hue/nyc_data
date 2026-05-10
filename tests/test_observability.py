"""Tests for observability, logging, and audit trail infrastructure.

Tests cover structured logging, operational context, and audit logs.
"""

import pytest
from datetime import datetime
from socrata_toolkit.observability import (
    OperationalLogger,
    OperationalContext,
    AuditLog,
    LogRecord,
    ActionType,
    LogLevel,
)


class TestLogRecord:
    """Tests for LogRecord class."""

    def test_log_record_creation(self):
        """Test basic log record creation."""
        record = LogRecord(
            timestamp=datetime.utcnow(),
            level="INFO",
            message="Test message",
            module="test_module",
            function_name="test_func",
            line_number=42,
            request_id="req-123",
        )
        assert record.level == "INFO"
        assert record.message == "Test message"

    def test_log_record_with_context(self):
        """Test log record with additional context."""
        record = LogRecord(
            timestamp=datetime.utcnow(),
            level="INFO",
            message="Test message",
            module="test_module",
            function_name="test_func",
            line_number=42,
            request_id="req-123",
            dataset_id="nyc-311",
            operation_type="ingestion",
            record_count=1500,
        )
        assert record.dataset_id == "nyc-311"
        assert record.record_count == 1500

    def test_log_record_to_dict(self):
        """Test log record to dictionary conversion."""
        record = LogRecord(
            timestamp=datetime.utcnow(),
            level="INFO",
            message="Test message",
            module="test_module",
            function_name="test_func",
            line_number=42,
            request_id="req-123",
        )
        d = record.to_dict()
        assert d["level"] == "INFO"
        assert d["message"] == "Test message"
        assert "timestamp" in d

    def test_log_record_to_json(self):
        """Test log record to JSON conversion."""
        record = LogRecord(
            timestamp=datetime.utcnow(),
            level="ERROR",
            message="Error occurred",
            module="error_module",
            function_name="error_func",
            line_number=100,
            request_id="req-456",
            error="Connection timeout",
        )
        json_str = record.to_json()
        assert "ERROR" in json_str
        assert "req-456" in json_str


class TestOperationalLogger:
    """Tests for OperationalLogger class."""

    def test_logger_initialization(self):
        """Test operational logger initialization."""
        logger = OperationalLogger("test_module")
        assert logger.name == "test_module"
        assert logger.request_id is not None

    def test_logger_info_message(self):
        """Test logging info message."""
        logger = OperationalLogger("test_module")
        logger.info("Test info message")
        # Should not raise error

    def test_logger_debug_message(self):
        """Test logging debug message."""
        logger = OperationalLogger("test_module")
        logger.debug("Test debug message")
        # Should not raise error

    def test_logger_warning_message(self):
        """Test logging warning message."""
        logger = OperationalLogger("test_module")
        logger.warning("Test warning message")
        # Should not raise error

    def test_logger_error_message(self):
        """Test logging error message."""
        logger = OperationalLogger("test_module")
        logger.error("Test error message")
        # Should not raise error

    def test_logger_critical_message(self):
        """Test logging critical message."""
        logger = OperationalLogger("test_module")
        logger.critical("Test critical message")
        # Should not raise error

    def test_logger_with_dataset_id(self):
        """Test logging with dataset ID."""
        logger = OperationalLogger("test_module")
        logger.info("Processing dataset", dataset_id="nyc-311")
        # Should not raise error

    def test_logger_with_operation_type(self):
        """Test logging with operation type."""
        logger = OperationalLogger("test_module")
        logger.info("Starting operation", operation_type="ingestion")
        # Should not raise error

    def test_logger_with_record_count(self):
        """Test logging with record count."""
        logger = OperationalLogger("test_module")
        logger.info("Processed records", record_count=1500)
        # Should not raise error

    def test_logger_with_duration(self):
        """Test logging with duration."""
        logger = OperationalLogger("test_module")
        logger.info("Operation completed", duration_seconds=2.5)
        # Should not raise error

    def test_logger_with_error_details(self):
        """Test logging error with details."""
        logger = OperationalLogger("test_module")
        logger.error("Operation failed", error="Network timeout")
        # Should not raise error

    def test_logger_with_context(self):
        """Test logging with additional context."""
        logger = OperationalLogger("test_module")
        context = {"extra_field": "extra_value", "count": 42}
        logger.info("Message with context", context=context)
        # Should not raise error

    def test_logger_request_id_consistency(self):
        """Test that logger maintains consistent request ID."""
        logger = OperationalLogger("test_module")
        req_id_1 = logger.request_id
        logger.info("First message")
        req_id_2 = logger.request_id
        assert req_id_1 == req_id_2

    def test_logger_with_full_parameters(self):
        """Test logging with all available parameters."""
        logger = OperationalLogger("test_module")
        logger.info(
            "Full test message",
            dataset_id="nyc-311",
            operation_type="ingestion",
            record_count=1500,
            duration_seconds=2.5,
            context={"status": "success"},
        )
        # Should not raise error


class TestOperationalContext:
    """Tests for OperationalContext class."""

    def test_context_initialization(self):
        """Test operational context initialization."""
        ctx = OperationalContext(
            operation_type="ingestion",
            dataset_id="nyc-311",
        )
        assert ctx.operation_type == "ingestion"
        assert ctx.dataset_id == "nyc-311"
        assert ctx.operation_id is not None

    def test_context_manager_success(self):
        """Test context manager for successful operation."""
        logger = OperationalLogger("test_module")
        with OperationalContext(
            operation_type="ingestion",
            dataset_id="nyc-311",
            logger=logger,
        ) as ctx:
            assert ctx.operation_id is not None
        # Should log start and end

    def test_context_manager_with_exception(self):
        """Test context manager captures exceptions."""
        logger = OperationalLogger("test_module")
        try:
            with OperationalContext(
                operation_type="ingestion",
                dataset_id="nyc-311",
                logger=logger,
            ):
                raise ValueError("Test error")
        except ValueError:
            pass
        # Should log the error

    def test_context_with_user(self):
        """Test context with user information."""
        ctx = OperationalContext(
            operation_type="data_access",
            user="user@example.com",
        )
        assert ctx.user == "user@example.com"

    def test_context_timing(self):
        """Test context timing tracking."""
        ctx = OperationalContext(operation_type="test")
        start_time = ctx.start_time
        assert start_time is not None
        assert isinstance(start_time, datetime)


class TestAuditLog:
    """Tests for AuditLog class."""

    def test_audit_log_initialization_no_db(self):
        """Test audit log initialization without database."""
        audit = AuditLog()
        assert audit.db_dsn is None

    def test_audit_log_initialization_with_table_name(self):
        """Test audit log with custom table name."""
        audit = AuditLog(table_name="custom_audit")
        assert audit.table_name == "custom_audit"

    def test_record_schema_change(self):
        """Test recording schema change."""
        audit = AuditLog()
        op_id = audit.record_action(
            ActionType.SCHEMA_CHANGE,
            dataset_id="nyc-311",
            actor="data_engineer",
            details={"columns_added": ["new_col"]},
        )
        assert op_id is not None

    def test_record_data_quality_gate(self):
        """Test recording data quality gate failure."""
        audit = AuditLog()
        op_id = audit.record_action(
            ActionType.DATA_QUALITY_GATE,
            dataset_id="nyc-311",
            details={"gate": "not_null_check", "status": "failed"},
        )
        assert op_id is not None

    def test_record_validation_failure(self):
        """Test recording validation failure."""
        audit = AuditLog()
        op_id = audit.record_action(
            ActionType.VALIDATION_FAILURE,
            dataset_id="nyc-311",
            details={"rule": "column_type_mismatch"},
            status="failure",
        )
        assert op_id is not None

    def test_record_access(self):
        """Test recording access event."""
        audit = AuditLog()
        op_id = audit.record_action(
            ActionType.ACCESS,
            dataset_id="nyc-311",
            actor="analyst@example.com",
            details={"query": "SELECT COUNT(*) FROM table"},
        )
        assert op_id is not None

    def test_record_deletion(self):
        """Test recording deletion event."""
        audit = AuditLog()
        op_id = audit.record_action(
            ActionType.DELETION,
            dataset_id="nyc-311",
            actor="admin",
            resource_id="record_123",
            details={"reason": "data_retention_policy"},
        )
        assert op_id is not None

    def test_record_modification(self):
        """Test recording modification event."""
        audit = AuditLog()
        op_id = audit.record_action(
            ActionType.MODIFICATION,
            dataset_id="nyc-311",
            actor="data_engineer",
            resource_id="record_456",
            details={"fields_changed": ["status", "updated_date"]},
        )
        assert op_id is not None

    def test_record_ingestion(self):
        """Test recording ingestion event."""
        audit = AuditLog()
        op_id = audit.record_action(
            ActionType.INGESTION,
            dataset_id="nyc-311",
            details={"records_ingested": 1500, "duration_seconds": 2.5},
        )
        assert op_id is not None

    def test_record_transformation(self):
        """Test recording transformation event."""
        audit = AuditLog()
        op_id = audit.record_action(
            ActionType.TRANSFORMATION,
            dataset_id="nyc-311",
            details={"source": "raw_dataset", "target": "cleaned_dataset"},
        )
        assert op_id is not None

    def test_audit_log_get_audit_trail_no_db(self):
        """Test getting audit trail when no database."""
        audit = AuditLog()
        trail = audit.get_audit_trail("nyc-311")
        assert trail == []

    def test_record_action_without_optional_fields(self):
        """Test recording action with minimal fields."""
        audit = AuditLog()
        op_id = audit.record_action(ActionType.INGESTION)
        assert op_id is not None

    def test_record_action_with_all_fields(self):
        """Test recording action with all available fields."""
        audit = AuditLog()
        op_id = audit.record_action(
            ActionType.SCHEMA_CHANGE,
            dataset_id="nyc-311",
            actor="data_engineer",
            resource_id="schema_version_5",
            details={"changes": ["column_added", "index_created"]},
            status="success",
        )
        assert op_id is not None


class TestObservabilityIntegration:
    """Integration tests for observability components."""

    def test_logger_and_audit_together(self):
        """Test using logger and audit log together."""
        logger = OperationalLogger("integration_test")
        audit = AuditLog()

        logger.info("Starting operation", dataset_id="nyc-311")
        op_id = audit.record_action(
            ActionType.INGESTION,
            dataset_id="nyc-311",
        )
        logger.info("Operation recorded", context={"operation_id": op_id})
        # Should work without error

    def test_context_with_logger_and_audit(self):
        """Test using context manager with logger and audit."""
        logger = OperationalLogger("context_test")
        audit = AuditLog()

        with OperationalContext(
            operation_type="ingestion",
            dataset_id="nyc-311",
            logger=logger,
        ) as ctx:
            op_id = audit.record_action(
                ActionType.INGESTION,
                dataset_id="nyc-311",
                details={"operation_id": ctx.operation_id},
            )
            assert op_id is not None

    def test_multiple_loggers(self):
        """Test using multiple loggers."""
        logger1 = OperationalLogger("module1")
        logger2 = OperationalLogger("module2")

        logger1.info("Message from module 1")
        logger2.info("Message from module 2")
        # Should work independently


class TestObservabilityEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_logger_with_none_values(self):
        """Test logger with None values in optional fields."""
        logger = OperationalLogger("test")
        logger.info(
            "Test message",
            dataset_id=None,
            operation_type=None,
            record_count=None,
            duration_seconds=None,
        )
        # Should not raise error

    def test_audit_log_with_large_details(self):
        """Test audit log with large details dictionary."""
        audit = AuditLog()
        large_details = {f"field_{i}": f"value_{i}" for i in range(100)}
        op_id = audit.record_action(
            ActionType.INGESTION,
            details=large_details,
        )
        assert op_id is not None

    def test_context_with_exception_type_capture(self):
        """Test context captures exception information."""
        logger = OperationalLogger("test")

        class CustomException(Exception):
            pass

        try:
            with OperationalContext(
                operation_type="test",
                logger=logger,
            ):
                raise CustomException("Custom error")
        except CustomException:
            pass
        # Should log the exception

    def test_audit_log_multiple_actions_same_dataset(self):
        """Test multiple audit actions on same dataset."""
        audit = AuditLog()
        dataset_id = "test-dataset"

        op_id_1 = audit.record_action(ActionType.INGESTION, dataset_id=dataset_id)
        op_id_2 = audit.record_action(ActionType.VALIDATION_FAILURE, dataset_id=dataset_id)
        op_id_3 = audit.record_action(ActionType.SCHEMA_CHANGE, dataset_id=dataset_id)

        assert op_id_1 != op_id_2
        assert op_id_2 != op_id_3

    def test_logger_long_message(self):
        """Test logger with very long message."""
        logger = OperationalLogger("test")
        long_message = "x" * 10000
        logger.info(long_message)
        # Should not raise error
