"""Unified observability, logging, and audit trail infrastructure.

This module provides structured logging with operational context, audit trails
for compliance, and integration with log aggregation systems (ELK, Grafana Loki).

Key Classes:
    - OperationalLogger: Enhanced logger with structured fields
    - OperationalContext: Context manager for request tracing
    - AuditLog: Immutable audit trail for compliance

Usage:
    logger = OperationalLogger(__name__)
    with OperationalContext(dataset_id='nyc-311', operation='ingestion'):
        logger.info('Processing dataset', extra={'record_count': 1500})

    audit = AuditLog(db_dsn='postgresql://...')
    audit.record_action('schema_change', dataset_id='nyc-311', ...)
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
import json
import logging
import logging.handlers
import sys
from typing import Any, Generator, Optional
import uuid

try:
    import psycopg
except ImportError:
    psycopg = None  # type: ignore


class LogLevel(Enum):
    """Logging level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ActionType(Enum):
    """Types of actions recorded in audit log."""
    SCHEMA_CHANGE = "schema_change"
    DATA_QUALITY_GATE = "data_quality_gate"
    VALIDATION_FAILURE = "validation_failure"
    ACCESS = "access"
    DELETION = "deletion"
    MODIFICATION = "modification"
    INGESTION = "ingestion"
    TRANSFORMATION = "transformation"


@dataclass
class LogRecord:
    """Structured log record with operational context.

    Attributes:
        timestamp: ISO 8601 timestamp when log was created
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        message: Log message text
        module: Module name where log originated
        function_name: Function name where log originated
        line_number: Line number where log originated
        request_id: Unique request identifier for tracing
        dataset_id: Dataset involved in operation
        operation_type: Type of operation (ingestion, validation, etc.)
        record_count: Optional count of records processed
        duration_seconds: Optional duration of operation
        error: Optional error details
        context: Optional additional context as dictionary
    """

    timestamp: datetime
    level: str
    message: str
    module: str
    function_name: str
    line_number: int
    request_id: str
    dataset_id: Optional[str] = None
    operation_type: Optional[str] = None
    record_count: Optional[int] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    context: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert log record to dictionary.

        Returns:
            dict: Log record as dictionary with ISO 8601 timestamp

        Examples:
            >>> record = LogRecord(
            ...     timestamp=datetime.utcnow(),
            ...     level='INFO',
            ...     message='Test message',
            ...     module='test_module',
            ...     function_name='test_func',
            ...     line_number=42,
            ...     request_id='req-123'
            ... )
            >>> d = record.to_dict()
            >>> d['level'] == 'INFO'
            True
        """
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat() + "Z"
        return d

    def to_json(self) -> str:
        """Convert log record to JSON.

        Returns:
            str: Log record as JSON string

        Examples:
            >>> record = LogRecord(
            ...     timestamp=datetime.utcnow(),
            ...     level='INFO',
            ...     message='Test message',
            ...     module='test_module',
            ...     function_name='test_func',
            ...     line_number=42,
            ...     request_id='req-123'
            ... )
            >>> json_str = record.to_json()
            >>> 'INFO' in json_str
            True
        """
        return json.dumps(self.to_dict())


class StructuredFormatter(logging.Formatter):
    """Formatter that outputs JSON with structured fields."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: logging.LogRecord instance

        Returns:
            str: JSON formatted log line
        """
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "dataset_id"):
            log_data["dataset_id"] = record.dataset_id
        if hasattr(record, "operation_type"):
            log_data["operation_type"] = record.operation_type
        if hasattr(record, "record_count"):
            log_data["record_count"] = record.record_count
        if hasattr(record, "duration_seconds"):
            log_data["duration_seconds"] = record.duration_seconds

        # Add extra context if present
        if hasattr(record, "context") and record.context:
            log_data["context"] = record.context

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class OperationalLogger:
    """Enhanced logger with structured fields and operational context.

    Provides consistent logging across modules with automatic inclusion
    of timestamp, module name, function name, line number, and request ID.

    Attributes:
        logger: Underlying Python logging.Logger instance
        name: Logger name
        request_id: Current request ID for tracing
    """

    def __init__(self, name: str, log_level: LogLevel = LogLevel.INFO):
        """Initialize operational logger.

        Args:
            name: Logger name (typically __name__)
            log_level: Minimum log level to capture

        Examples:
            >>> logger = OperationalLogger('my_module')
            >>> logger.info('Operation started', extra={'dataset_id': 'nyc-311'})
        """
        self.logger = logging.getLogger(name)
        self.name = name
        self.request_id = str(uuid.uuid4())

        # Set up handlers
        if not self.logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level.name)
            console_formatter = StructuredFormatter()
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

            # File handler (rotating)
            try:
                file_handler = logging.handlers.RotatingFileHandler(
                    f"logs/{name.replace('.', '_')}.log",
                    maxBytes=10485760,  # 10MB
                    backupCount=5,
                )
                file_handler.setLevel(log_level.name)
                file_handler.setFormatter(console_formatter)
                self.logger.addHandler(file_handler)
            except (FileNotFoundError, PermissionError):
                # Log directory might not exist, skip file handler
                pass

        self.logger.setLevel(log_level.name)

    def _log(
        self,
        level: str,
        message: str,
        dataset_id: Optional[str] = None,
        operation_type: Optional[str] = None,
        record_count: Optional[int] = None,
        duration_seconds: Optional[float] = None,
        error: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> None:
        """Internal logging method with structured fields.

        Args:
            level: Log level name
            message: Log message
            dataset_id: Optional dataset identifier
            operation_type: Optional operation type
            record_count: Optional record count
            duration_seconds: Optional operation duration
            error: Optional error details
            context: Optional additional context dictionary
        """
        import inspect
        frame = inspect.currentframe()
        caller_frame = frame.f_back.f_back if frame and frame.f_back else None
        lineno = caller_frame.f_lineno if caller_frame else 0

        # Create extra dict for logging
        extra = {
            "request_id": self.request_id,
            "dataset_id": dataset_id,
            "operation_type": operation_type,
            "record_count": record_count,
            "duration_seconds": duration_seconds,
            "context": context or {},
        }

        # Use getattr to avoid passing undefined attributes
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(message, extra=extra)

    def debug(
        self,
        message: str,
        dataset_id: Optional[str] = None,
        operation_type: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> None:
        """Log debug message.

        Args:
            message: Log message
            dataset_id: Optional dataset ID
            operation_type: Optional operation type
            context: Optional context dictionary

        Examples:
            >>> logger = OperationalLogger('test')
            >>> logger.debug('Debug message', dataset_id='nyc-311')
        """
        self._log("DEBUG", message, dataset_id, operation_type, context=context)

    def info(
        self,
        message: str,
        dataset_id: Optional[str] = None,
        operation_type: Optional[str] = None,
        record_count: Optional[int] = None,
        duration_seconds: Optional[float] = None,
        context: Optional[dict] = None,
    ) -> None:
        """Log info message.

        Args:
            message: Log message
            dataset_id: Optional dataset ID
            operation_type: Optional operation type
            record_count: Optional record count
            duration_seconds: Optional duration
            context: Optional context dictionary

        Examples:
            >>> logger = OperationalLogger('test')
            >>> logger.info('Ingestion complete', dataset_id='nyc-311', record_count=1500)
        """
        self._log(
            "INFO",
            message,
            dataset_id,
            operation_type,
            record_count,
            duration_seconds,
            context=context,
        )

    def warning(
        self,
        message: str,
        dataset_id: Optional[str] = None,
        operation_type: Optional[str] = None,
        error: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> None:
        """Log warning message.

        Args:
            message: Log message
            dataset_id: Optional dataset ID
            operation_type: Optional operation type
            error: Optional error details
            context: Optional context dictionary

        Examples:
            >>> logger = OperationalLogger('test')
            >>> logger.warning('SLA violation detected', dataset_id='nyc-311')
        """
        self._log("WARNING", message, dataset_id, operation_type, error=error, context=context)

    def error(
        self,
        message: str,
        dataset_id: Optional[str] = None,
        operation_type: Optional[str] = None,
        error: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> None:
        """Log error message.

        Args:
            message: Log message
            dataset_id: Optional dataset ID
            operation_type: Optional operation type
            error: Error details
            context: Optional context dictionary

        Examples:
            >>> logger = OperationalLogger('test')
            >>> logger.error('Ingestion failed', dataset_id='nyc-311', error='Network timeout')
        """
        self._log("ERROR", message, dataset_id, operation_type, error=error, context=context)

    def critical(
        self,
        message: str,
        dataset_id: Optional[str] = None,
        operation_type: Optional[str] = None,
        error: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> None:
        """Log critical message.

        Args:
            message: Log message
            dataset_id: Optional dataset ID
            operation_type: Optional operation type
            error: Error details
            context: Optional context dictionary

        Examples:
            >>> logger = OperationalLogger('test')
            >>> logger.critical('System failure', error='Database connection lost')
        """
        self._log("CRITICAL", message, dataset_id, operation_type, error=error, context=context)


@dataclass
class OperationalContext:
    """Context manager for tracing request flow through pipeline.

    Tracks operation start/end, duration, success/failure, and record counts.

    Attributes:
        operation_id: Unique operation identifier
        operation_type: Type of operation (ingestion, validation, etc.)
        dataset_id: Dataset involved in operation
        user: Optional user/service performing operation
        start_time: ISO 8601 start timestamp
    """

    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation_type: str = ""
    dataset_id: Optional[str] = None
    user: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.utcnow)
    logger: Optional[OperationalLogger] = None

    def __enter__(self) -> OperationalContext:
        """Enter context: log operation start.

        Returns:
            self: OperationalContext instance

        Examples:
            >>> with OperationalContext(operation_type='ingestion', dataset_id='nyc-311') as ctx:
            ...     print(ctx.operation_id)
        """
        if self.logger:
            self.logger.info(
                f"Operation started: {self.operation_type}",
                dataset_id=self.dataset_id,
                operation_type=self.operation_type,
            )
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context: log operation end with duration.

        Args:
            exc_type: Exception type if operation failed
            exc_val: Exception value if operation failed
            exc_tb: Exception traceback if operation failed
        """
        duration = (datetime.utcnow() - self.start_time).total_seconds()

        if exc_type is None:
            if self.logger:
                self.logger.info(
                    f"Operation completed: {self.operation_type}",
                    dataset_id=self.dataset_id,
                    operation_type=self.operation_type,
                    duration_seconds=duration,
                )
        else:
            if self.logger:
                self.logger.error(
                    f"Operation failed: {self.operation_type}",
                    dataset_id=self.dataset_id,
                    operation_type=self.operation_type,
                    error=str(exc_val),
                )


class AuditLog:
    """Immutable audit trail for compliance and data governance.

    Records all significant operations for audit, compliance, and investigation.

    Attributes:
        db_dsn: PostgreSQL connection string
        table_name: Table name for audit log storage
    """

    def __init__(self, db_dsn: Optional[str] = None, table_name: str = "audit_log"):
        """Initialize audit log.

        Args:
            db_dsn: PostgreSQL connection string (optional)
            table_name: Table name for audit log
        """
        self.db_dsn = db_dsn
        self.table_name = table_name
        self.logger = OperationalLogger(__name__)

        if self.db_dsn and psycopg:
            self._init_db()

    def _init_db(self) -> None:
        """Initialize PostgreSQL audit log table."""
        if not self.db_dsn:
            return

        try:
            with psycopg.connect(self.db_dsn) as conn:
                with conn.cursor() as cur:
                    # Create audit log table (immutable append-only)
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS {self.table_name} (
                            id BIGSERIAL PRIMARY KEY,
                            operation_id UUID NOT NULL,
                            actor VARCHAR(255),
                            action_type VARCHAR(50) NOT NULL,
                            dataset_id VARCHAR(255),
                            resource_id VARCHAR(255),
                            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                            details JSONB,
                            status VARCHAR(20)
                        );
                    """)

                    # Add indexes for fast queries
                    cur.execute(f"""
                        CREATE INDEX IF NOT EXISTS {self.table_name}_operation_id_idx
                        ON {self.table_name} (operation_id);
                    """)

                    cur.execute(f"""
                        CREATE INDEX IF NOT EXISTS {self.table_name}_dataset_id_idx
                        ON {self.table_name} (dataset_id);
                    """)

                    cur.execute(f"""
                        CREATE INDEX IF NOT EXISTS {self.table_name}_action_type_idx
                        ON {self.table_name} (action_type);
                    """)

                    cur.execute(f"""
                        CREATE INDEX IF NOT EXISTS {self.table_name}_timestamp_idx
                        ON {self.table_name} (timestamp DESC);
                    """)

                    # Disable direct updates/deletes on audit table (append-only)
                    cur.execute(f"""
                        ALTER TABLE {self.table_name} ENABLE ROW LEVEL SECURITY;
                    """)

                    conn.commit()
                    self.logger.info(f"Initialized audit log table: {self.table_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize audit log: {e}")

    def record_action(
        self,
        action_type: ActionType,
        dataset_id: Optional[str] = None,
        actor: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[dict] = None,
        status: str = "success",
    ) -> str:
        """Record action in audit log.

        Args:
            action_type: Type of action
            dataset_id: Optional dataset involved
            actor: Optional user/service performing action
            resource_id: Optional resource identifier
            details: Optional detailed information as dictionary
            status: Operation status (success, failure)

        Returns:
            str: Operation ID for tracing

        Examples:
            >>> audit = AuditLog()
            >>> op_id = audit.record_action(
            ...     ActionType.SCHEMA_CHANGE,
            ...     dataset_id='nyc-311',
            ...     details={'columns_added': ['new_col']}
            ... )
        """
        operation_id = str(uuid.uuid4())

        if self.db_dsn and psycopg:
            self._persist_action(operation_id, action_type, dataset_id, actor, resource_id, details, status)

        self.logger.info(
            f"Audit log: {action_type.value}",
            dataset_id=dataset_id,
            operation_type=action_type.value,
            context={"operation_id": operation_id, "status": status},
        )

        return operation_id

    def _persist_action(
        self,
        operation_id: str,
        action_type: ActionType,
        dataset_id: Optional[str],
        actor: Optional[str],
        resource_id: Optional[str],
        details: Optional[dict],
        status: str,
    ) -> None:
        """Persist action to PostgreSQL."""
        if not self.db_dsn:
            return

        try:
            with psycopg.connect(self.db_dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        INSERT INTO {self.table_name}
                        (operation_id, actor, action_type, dataset_id, resource_id, details, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            operation_id,
                            actor,
                            action_type.value,
                            dataset_id,
                            resource_id,
                            json.dumps(details or {}),
                            status,
                        ),
                    )
                    conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to persist audit log entry: {e}")

    def get_audit_trail(self, dataset_id: str, limit: int = 100) -> list[dict]:
        """Retrieve audit trail for dataset.

        Args:
            dataset_id: Dataset identifier
            limit: Maximum number of records to return

        Returns:
            list of audit log entries

        Examples:
            >>> audit = AuditLog(db_dsn='postgresql://...')
            >>> trail = audit.get_audit_trail('nyc-311')
            >>> print(f"Found {len(trail)} audit entries")
        """
        if not self.db_dsn:
            return []

        try:
            with psycopg.connect(self.db_dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT operation_id, actor, action_type, timestamp, details, status
                        FROM {self.table_name}
                        WHERE dataset_id = %s
                        ORDER BY timestamp DESC
                        LIMIT %s
                        """,
                        (dataset_id, limit),
                    )

                    rows = cur.fetchall()
                    return [
                        {
                            "operation_id": row[0],
                            "actor": row[1],
                            "action_type": row[2],
                            "timestamp": row[3].isoformat() + "Z",
                            "details": row[4],
                            "status": row[5],
                        }
                        for row in rows
                    ]
        except Exception as e:
            self.logger.error(f"Failed to retrieve audit trail: {e}")
            return []
