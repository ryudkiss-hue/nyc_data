"""Structured log capture and querying for the observability subsystem."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class LogEntry:
    """A single structured log record."""

    message: str
    level: str = "INFO"
    logger_name: str = "socrata_toolkit"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: str | None = None
    dataset_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "logger_name": self.logger_name,
            "message": self.message,
            "correlation_id": self.correlation_id,
            "dataset_id": self.dataset_id,
            "context": self.context,
        }

class LogStore:
    """In-memory ring buffer of structured log entries with filtering."""

    def __init__(self, max_entries: int = 10000) -> None:
        self.max_entries = max_entries
        self._entries: list[LogEntry] = []

    def add(self, entry: LogEntry) -> None:
        self._entries.append(entry)
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries:]

    def log(self, message: str, level: str = "INFO", **kwargs: Any) -> LogEntry:
        entry = LogEntry(message=message, level=level, **kwargs)
        self.add(entry)
        return entry

    def query(
        self,
        level: str | None = None,
        correlation_id: str | None = None,
        dataset_id: str | None = None,
    ) -> list[LogEntry]:
        results = self._entries
        if level:
            results = [e for e in results if e.level == level]
        if correlation_id:
            results = [e for e in results if e.correlation_id == correlation_id]
        if dataset_id:
            results = [e for e in results if e.dataset_id == dataset_id]
        return list(results)

    def __len__(self) -> int:
        return len(self._entries)

    # -- export ---------------------------------------------------------
    def export_json(self, path: str | Path) -> None:
        data = [e.to_dict() for e in self._entries]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def export_csv(self, path: str | Path) -> None:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "level", "logger_name", "message", "correlation_id", "dataset_id"])
            for e in self._entries:
                writer.writerow([e.timestamp, e.level, e.logger_name, e.message, e.correlation_id, e.dataset_id])

    def clear(self) -> None:
        self._entries.clear()
