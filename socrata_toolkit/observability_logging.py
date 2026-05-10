"""Structured logging with correlation IDs and context propagation.

This module provides production-grade structured logging with:
- JSON-formatted output with correlation IDs
- Thread-local context propagation
- Circular buffer for in-memory log storage
- Multiple export backends (filesystem, remote)

Usage:
    logger = StructuredLogger(__name__)
    with LogContext(dataset_id='nyc-311', correlation_id='req-123'):
        logger.info('Processing dataset', extra={'record_count': 1500})
"""

from __future__ import annotations

import contextvars
import io
import json
import logging
import logging.handlers
import queue
import threading
import time
import traceback
import uuid
from collections import deque
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogRecord:
    """Structured log record with operational context.
    
    Attributes:
        timestamp: ISO 8601 timestamp in UTC
        level: Log level (DEBUG, INFO, WARN, ERROR, CRITICAL)
        logger_name: Name of the logger
        correlation_id: Unique correlation ID for request tracing
        user: Optional user identifier
        message: Log message
        context: Dictionary of contextual fields (dataset_id, node_id, etc.)
        exception: Optional exception information
        duration_ms: Optional operation duration in milliseconds
    """
    timestamp: str
    level: str
    logger_name: str
    correlation_id: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    user: Optional[str] = None
    exception: Optional[str] = None
    duration_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Remove None values for cleaner JSON
        return {k: v for k, v in data.items() if v is not None}

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class LogContext:
    """Thread-local context manager for correlation IDs and contextual fields.
    
    Maintains a stack of contexts, allowing nested operations to have
    their own context while inheriting parent context.
    
    Example:
        with LogContext(dataset_id='nyc-311'):
            logger.info('Processing')  # Has dataset_id in context
            with LogContext(node_id='node-1'):
                logger.info('Node work')  # Has both dataset_id and node_id
    """
    
    # Thread-local storage for context stacks
    _context_var: contextvars.ContextVar[List[Dict[str, Any]]] = \
        contextvars.ContextVar('log_context', default=[])

    def __init__(self, correlation_id: Optional[str] = None, **fields: Any):
        """Initialize context with optional correlation ID and fields.
        
        Args:
            correlation_id: Optional correlation ID (generated if not provided)
            **fields: Contextual fields (dataset_id, user, etc.)
        """
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.fields = fields
        self._token: Optional[contextvars.Token] = None

    def __enter__(self) -> LogContext:
        """Enter context, pushing to stack."""
        stack = list(self._context_var.get())
        
        # Merge with parent context (child overrides parent)
        merged = {}
        if stack:
            merged.update(stack[-1])
        merged.update(self.fields)
        merged['correlation_id'] = self.correlation_id
        
        stack.append(merged)
        self._token = self._context_var.set(stack)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context, popping from stack."""
        if self._token is not None:
            stack = list(self._context_var.get())
            if stack:
                stack.pop()
            self._context_var.set(stack)

    @classmethod
    def get_current(cls) -> Dict[str, Any]:
        """Get current context dictionary."""
        stack = cls._context_var.get()
        if stack:
            return dict(stack[-1])
        return {'correlation_id': str(uuid.uuid4())}

    @classmethod
    def get_correlation_id(cls) -> str:
        """Get current correlation ID."""
        context = cls.get_current()
        return context.get('correlation_id', str(uuid.uuid4()))


class StructuredLogger:
    """Production-grade structured logger with correlation ID tracking.
    
    All log messages are formatted as JSON with correlation IDs and
    contextual information. Thread-safe and integrates with Python's
    standard logging.
    
    Example:
        logger = StructuredLogger(__name__)
        logger.info('Task completed', extra={'duration_ms': 123.4})
    """

    def __init__(self, name: str):
        """Initialize logger.
        
        Args:
            name: Logger name (typically __name__)
        """
        self.name = name
        self._logger = logging.getLogger(name)

    def _format_record(
        self,
        level: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None,
    ) -> LogRecord:
        """Format a log record with context.
        
        Args:
            level: Log level
            message: Log message
            extra: Optional extra fields to include
            exc_info: Optional exception
            
        Returns:
            LogRecord with all fields populated
        """
        context = LogContext.get_current()
        correlation_id = context.get('correlation_id', str(uuid.uuid4()))
        
        # Build context from LogContext and extra fields
        ctx = {k: v for k, v in context.items() if k != 'correlation_id'}
        if extra:
            ctx.update(extra)

        # Extract common fields if in extra
        duration_ms = ctx.pop('duration_ms', None)
        user = ctx.pop('user', None)

        # Capture exception if provided
        exception_str = None
        if exc_info:
            if isinstance(exc_info, Exception):
                exception_str = ''.join(
                    traceback.format_exception(type(exc_info), exc_info, exc_info.__traceback__)
                )
            else:
                exception_str = str(exc_info)

        return LogRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            logger_name=self.name,
            correlation_id=correlation_id,
            message=message,
            context=ctx,
            user=user,
            exception=exception_str,
            duration_ms=duration_ms,
        )

    def _log(
        self,
        level: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None,
    ) -> None:
        """Internal logging method."""
        record = self._format_record(level, message, extra, exc_info)
        
        # Log to Python logging system
        py_level = getattr(logging, level, logging.INFO)
        self._logger.log(py_level, record.to_json())

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message."""
        self._log('DEBUG', message, extra)

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log info message."""
        self._log('INFO', message, extra)

    def warn(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message."""
        self._log('WARN', message, extra)

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log error message."""
        self._log('ERROR', message, extra)

    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log critical message."""
        self._log('CRITICAL', message, extra)

    def exception(self, message: str, exc_info: Exception, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log exception with traceback."""
        self._log('ERROR', message, extra, exc_info)

    @contextmanager
    def timeit(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Context manager to time operations.
        
        Example:
            with logger.timeit('ingestion', extra={'dataset': 'nyc-311'}):
                # do work
        """
        start = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start) * 1000
            log_extra = extra or {}
            log_extra['duration_ms'] = duration_ms
            self.info(message, extra=log_extra)


class CircularLogBuffer:
    """Thread-safe circular buffer for in-memory log storage.
    
    Keeps only the most recent N log records in memory, dropping oldest
    when buffer is full. Provides efficient log querying by level, 
    correlation_id, and time range.
    
    Args:
        max_size: Maximum number of log records to keep (default: 10000)
    """

    def __init__(self, max_size: int = 10000):
        """Initialize circular buffer."""
        self.max_size = max_size
        self._buffer: deque[LogRecord] = deque(maxlen=max_size)
        self._lock = threading.RLock()

    def append(self, record: LogRecord) -> None:
        """Add a log record to the buffer."""
        with self._lock:
            self._buffer.append(record)

    def get_all(self) -> List[LogRecord]:
        """Get all log records."""
        with self._lock:
            return list(self._buffer)

    def filter_by_level(self, level: str) -> List[LogRecord]:
        """Get logs by level."""
        with self._lock:
            return [r for r in self._buffer if r.level == level]

    def filter_by_correlation_id(self, correlation_id: str) -> List[LogRecord]:
        """Get logs by correlation ID."""
        with self._lock:
            return [r for r in self._buffer if r.correlation_id == correlation_id]

    def filter_by_context(self, **kwargs: Any) -> List[LogRecord]:
        """Filter logs by context fields.
        
        Example:
            logs = buffer.filter_by_context(dataset_id='nyc-311', node_id='node-1')
        """
        with self._lock:
            results = []
            for r in self._buffer:
                match = True
                for key, value in kwargs.items():
                    if r.context.get(key) != value:
                        match = False
                        break
                if match:
                    results.append(r)
            return results

    def filter_by_time_range(self, start_iso: str, end_iso: str) -> List[LogRecord]:
        """Filter logs by ISO 8601 timestamp range."""
        with self._lock:
            results = []
            for r in self._buffer:
                if start_iso <= r.timestamp <= end_iso:
                    results.append(r)
            return results

    def size(self) -> int:
        """Get current buffer size."""
        with self._lock:
            return len(self._buffer)


class LogAggregator:
    """Manages log export to file system and remote backends.
    
    Provides circular buffer for in-memory logs and handles export
    to filesystem (with daily rotation) and optional remote backends.
    """

    def __init__(
        self,
        buffer_size: int = 10000,
        log_dir: Optional[Path] = None,
        enable_file_export: bool = True,
    ):
        """Initialize log aggregator.
        
        Args:
            buffer_size: Size of circular buffer
            log_dir: Directory for log files (default: ./logs)
            enable_file_export: Whether to export to files
        """
        self.buffer = CircularLogBuffer(buffer_size)
        self.log_dir = Path(log_dir or './logs')
        self.enable_file_export = enable_file_export
        self._lock = threading.RLock()
        self._current_date = datetime.now(timezone.utc).date()

        if enable_file_export:
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def append(self, record: LogRecord) -> None:
        """Append log record."""
        with self._lock:
            self.buffer.append(record)
            if self.enable_file_export:
                self._export_to_file(record)

    def _export_to_file(self, record: LogRecord) -> None:
        """Export record to daily log file."""
        today = datetime.now(timezone.utc).date()
        
        # Rotate log file if date changed
        if today != self._current_date:
            self._current_date = today

        log_file = self.log_dir / f"app-{today.isoformat()}.jsonl"
        try:
            with open(log_file, 'a') as f:
                f.write(record.to_json() + '\n')
        except Exception:
            pass  # Fail silently to avoid log errors breaking application

    def export_json(self, filepath: Path, **filters: Any) -> None:
        """Export logs to JSON file.
        
        Args:
            filepath: Output file path
            **filters: Filter criteria (level, correlation_id, context fields)
        """
        if 'level' in filters:
            logs = self.buffer.filter_by_level(filters['level'])
        elif 'correlation_id' in filters:
            logs = self.buffer.filter_by_correlation_id(filters['correlation_id'])
        else:
            logs = self.buffer.get_all()

        data = [r.to_dict() for r in logs]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def export_csv(self, filepath: Path, **filters: Any) -> None:
        """Export logs to CSV file."""
        import csv

        if 'level' in filters:
            logs = self.buffer.filter_by_level(filters['level'])
        elif 'correlation_id' in filters:
            logs = self.buffer.filter_by_correlation_id(filters['correlation_id'])
        else:
            logs = self.buffer.get_all()

        if not logs:
            return

        # Flatten context fields for CSV
        rows = []
        for r in logs:
            row = r.to_dict()
            ctx = row.pop('context', {})
            row.update(ctx)
            rows.append(row)

        # Get all unique keys
        all_keys = set()
        for row in rows:
            all_keys.update(row.keys())
        all_keys = sorted(all_keys)

        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=all_keys)
            writer.writeheader()
            writer.writerows(rows)

    def query(self, **filters: Any) -> List[LogRecord]:
        """Query logs with filters.
        
        Supported filters:
            - level: str (DEBUG, INFO, WARN, ERROR, CRITICAL)
            - correlation_id: str
            - start_time: ISO 8601 string
            - end_time: ISO 8601 string
            - context fields: dataset_id, node_id, etc.
        """
        results = self.buffer.get_all()

        if 'level' in filters:
            results = [r for r in results if r.level == filters['level']]

        if 'correlation_id' in filters:
            results = [r for r in results if r.correlation_id == filters['correlation_id']]

        if 'start_time' in filters:
            results = [r for r in results if r.timestamp >= filters['start_time']]

        if 'end_time' in filters:
            results = [r for r in results if r.timestamp <= filters['end_time']]

        # Filter by context fields
        context_filters = {k: v for k, v in filters.items() 
                          if k not in ('level', 'correlation_id', 'start_time', 'end_time')}
        if context_filters:
            results = [r for r in results 
                      if all(r.context.get(k) == v for k, v in context_filters.items())]

        return results


# Global aggregator instance
_log_aggregator: Optional[LogAggregator] = None


def get_log_aggregator() -> LogAggregator:
    """Get or create global log aggregator."""
    global _log_aggregator
    if _log_aggregator is None:
        _log_aggregator = LogAggregator()
    return _log_aggregator


class JSONFormatter(logging.Formatter):
    """Formatter for JSON log output."""
    def format(self, record: logging.LogRecord) -> str:
        # Assume the message is already JSON from StructuredLogger
        return record.getMessage()


def setup_logging(
    level: str = 'INFO',
    log_file: Optional[Path] = None,
    json_output: bool = True,
) -> None:
    """Configure structured logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARN, ERROR, CRITICAL)
        log_file: Optional log file path
        json_output: Whether to use JSON output
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level, logging.INFO))

    # Remove existing handlers
    root.handlers.clear()

    # Console handler with JSON formatter
    console_handler = logging.StreamHandler()
    
    if json_output:
        console_handler.setFormatter(JSONFormatter())
    
    root.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        if json_output:
            file_handler.setFormatter(JSONFormatter())
        root.addHandler(file_handler)
