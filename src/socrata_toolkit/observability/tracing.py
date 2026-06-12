"""Lightweight distributed-tracing primitives (spans and traces)."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Span:
    """A single unit of work within a trace."""

    operation_name: str
    trace_id: str
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_span_id: str | None = None
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    status: str = "ok"
    error_message: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float | None:
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000.0

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def finish(self, status: str = "ok", error_message: str | None = None) -> None:
        self.end_time = time.time()
        self.status = status
        if error_message:
            self.error_message = error_message
            self.status = "error"

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "attributes": self.attributes,
        }

class Tracer:
    """Creates and stores spans grouped by trace id."""

    def __init__(self) -> None:
        self._traces: dict[str, list[Span]] = {}

    def start_span(
        self,
        operation_name: str,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
    ) -> Span:
        tid = trace_id or uuid.uuid4().hex[:16]
        span = Span(operation_name=operation_name, trace_id=tid, parent_span_id=parent_span_id)
        self._traces.setdefault(tid, []).append(span)
        return span

    def get_trace(self, trace_id: str) -> list[Span] | None:
        return self._traces.get(trace_id)

    def all_spans(self) -> list[Span]:
        return [s for spans in self._traces.values() for s in spans]

    def export_jaeger(self) -> str:
        """Export traces in a Jaeger-like JSON structure."""
        import json

        data = {
            "data": [
                {
                    "traceID": tid,
                    "spans": [s.to_dict() for s in spans],
                }
                for tid, spans in self._traces.items()
            ]
        }
        return json.dumps(data, indent=2, default=str)

    def clear(self) -> None:
        self._traces.clear()
