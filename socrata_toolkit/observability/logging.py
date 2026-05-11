"""Structured logging for observability and event tracking."""
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
import threading

__all__ = ["StructuredLogger", "get_event_log", "CircularLogBuffer", "LogAggregator", "LogContext", "LogRecord", "get_log_aggregator", "setup_logging"]

@dataclass
class LogRecord:
    timestamp: str
    level: str
    logger_name: str
    correlation_id: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

class LogContext:
    _storage = threading.local()

    def __init__(self, **kwargs):
        self.context = kwargs
        self.previous = None

    def __enter__(self):
        self.previous = getattr(self._storage, "current", {})
        new_ctx = self.previous.copy()
        new_ctx.update(self.context)
        if "correlation_id" not in new_ctx:
            new_ctx["correlation_id"] = str(uuid.uuid4())
        self._storage.current = new_ctx
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._storage.current = self.previous

    @classmethod
    def get_current(cls) -> Dict[str, Any]:
        return getattr(cls._storage, "current", {})

class StructuredLogger:
    def __init__(self, name: str):
        self.name = name

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self._log("INFO", message, extra)

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self._log("ERROR", message, extra)

    def _log(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None):
        ctx = LogContext.get_current()
        corr_id = ctx.get("correlation_id", "unknown")
        
        full_ctx = ctx.copy()
        if extra:
            full_ctx.update(extra)
            
        record = LogRecord(
            timestamp=datetime.now().isoformat(),
            level=level,
            logger_name=self.name,
            correlation_id=corr_id,
            message=message,
            context=full_ctx
        )
        # In a real system, we'd emit this record to a handler or buffer

class CircularLogBuffer:
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.buffer: List[LogRecord] = []

    def append(self, record: LogRecord):
        self.buffer.append(record)
        if len(self.buffer) > self.max_size:
            self.buffer.pop(0)

    def size(self) -> int:
        return len(self.buffer)

    def filter_by_level(self, level: str) -> List[LogRecord]:
        return [r for r in self.buffer if r.level == level]

    def filter_by_correlation_id(self, correlation_id: str) -> List[LogRecord]:
        return [r for r in self.buffer if r.correlation_id == correlation_id]

class LogAggregator:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.records: List[LogRecord] = []
        if not self.log_dir.exists():
            self.log_dir.mkdir(parents=True)

    def append(self, record: LogRecord):
        self.records.append(record)

    def export_json(self, export_file: Path):
        data = [r.to_dict() for r in self.records]
        with open(export_file, 'w') as f:
            json.dump(data, f)

def get_event_log() -> List[Dict[str, Any]]:
    return []

_global_aggregator: Optional[LogAggregator] = None

def get_log_aggregator() -> LogAggregator:
    global _global_aggregator
    if _global_aggregator is None:
        _global_aggregator = LogAggregator(log_dir=Path("./logs"))
    return _global_aggregator

def setup_logging(level: str = "INFO", json_output: bool = True):
    """Setup logging configuration."""
    pass
