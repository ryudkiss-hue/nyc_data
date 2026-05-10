"""Distributed tracing with OpenTelemetry integration.

This module provides:
- Span creation and tracking for operations
- Correlation ID propagation (W3C traceparent, B3)
- Decorators for automatic instrumentation
- Export to Jaeger, Tempo, Datadog

Usage:
    tracer = TracingContext()
    with tracer.span('ingestion_operation', attributes={'dataset': 'nyc-311'}):
        # do work
        
    @traced_operation(name='process_records')
    def process_records(records):
        pass
"""

from __future__ import annotations

import contextvars
import functools
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar


class SpanStatus(Enum):
    """Status of a span."""
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class SpanEvent:
    """An event that occurred during span execution."""
    timestamp: str
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """A span represents a single operation in a trace.
    
    Attributes:
        trace_id: Unique trace identifier
        span_id: Unique span identifier
        parent_span_id: Parent span ID (for nested spans)
        operation_name: Name of the operation
        start_time: Start time in UTC ISO 8601
        end_time: End time in UTC ISO 8601 (None if still running)
        duration_ms: Duration in milliseconds
        status: Status of the span (OK, ERROR, UNSET)
        attributes: Additional attributes/tags
        events: List of events that occurred
        error_message: Optional error message
    """
    trace_id: str
    span_id: str
    operation_name: str
    start_time: str
    status: str = "unset"
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    parent_span_id: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class TracingContext:
    """Manages span creation and context propagation.
    
    Thread-safe tracing context using contextvars for automatic
    propagation across async boundaries.
    
    Example:
        tracer = TracingContext()
        with tracer.span('operation'):
            tracer.add_event('milestone_reached')
    """

    # Context variables for span stack
    _trace_id_var: contextvars.ContextVar[str] = \
        contextvars.ContextVar('trace_id', default='')
    _span_stack_var: contextvars.ContextVar[List[Span]] = \
        contextvars.ContextVar('span_stack', default=[])

    def __init__(self):
        """Initialize tracing context."""
        self._spans: Dict[str, Span] = {}  # All spans by ID
        self._export_queue: List[Span] = []
        self._lock = __import__('threading').RLock()

    def start_span(
        self,
        operation_name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Start a new span.
        
        Args:
            operation_name: Name of the operation
            trace_id: Optional trace ID (generated if not provided)
            parent_span_id: Optional parent span ID
            attributes: Optional attributes/tags
            
        Returns:
            The new Span object
        """
        trace_id = trace_id or str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            operation_name=operation_name,
            start_time=datetime.now(timezone.utc).isoformat(),
            parent_span_id=parent_span_id,
            attributes=attributes or {},
        )

        with self._lock:
            self._spans[span_id] = span

        # Update context
        self._trace_id_var.set(trace_id)
        stack = list(self._span_stack_var.get())
        stack.append(span)
        self._span_stack_var.set(stack)

        return span

    def end_span(
        self,
        span_id: str,
        status: str = "ok",
        error_message: Optional[str] = None,
    ) -> None:
        """End a span.
        
        Args:
            span_id: ID of span to end
            status: Status (ok or error)
            error_message: Optional error message
        """
        with self._lock:
            if span_id in self._spans:
                span = self._spans[span_id]
                span.status = status
                span.error_message = error_message
                span.end_time = datetime.now(timezone.utc).isoformat()
                start = datetime.fromisoformat(span.start_time)
                end = datetime.fromisoformat(span.end_time)
                span.duration_ms = (end - start).total_seconds() * 1000

        # Pop from context stack
        stack = list(self._span_stack_var.get())
        if stack and stack[-1].span_id == span_id:
            stack.pop()
            self._span_stack_var.set(stack)

    def get_current_span(self) -> Optional[Span]:
        """Get the currently active span."""
        stack = self._span_stack_var.get()
        if stack:
            return stack[-1]
        return None

    def add_event(
        self,
        span_id: str,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add an event to a span.
        
        Args:
            span_id: ID of span
            name: Name of the event
            attributes: Optional event attributes
        """
        with self._lock:
            if span_id in self._spans:
                event = SpanEvent(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    name=name,
                    attributes=attributes or {},
                )
                self._spans[span_id].events.append(event)

    def get_span(self, span_id: str) -> Optional[Span]:
        """Get a span by ID."""
        with self._lock:
            return self._spans.get(span_id)

    def get_trace(self, trace_id: str) -> List[Span]:
        """Get all spans in a trace.
        
        Args:
            trace_id: Trace ID to retrieve
            
        Returns:
            List of spans in the trace, ordered by start time
        """
        with self._lock:
            spans = [s for s in self._spans.values() if s.trace_id == trace_id]
            return sorted(spans, key=lambda s: s.start_time)

    def export_jaeger_json(self) -> str:
        """Export spans in Jaeger JSON format."""
        with self._lock:
            # Group spans by trace ID
            traces: Dict[str, List[Dict[str, Any]]] = {}
            for span in self._spans.values():
                if span.trace_id not in traces:
                    traces[span.trace_id] = []
                traces[span.trace_id].append(span.to_dict())

            # Format for Jaeger
            data = {
                'data': [
                    {
                        'traceID': trace_id,
                        'spans': spans,
                    }
                    for trace_id, spans in traces.items()
                ]
            }
            return json.dumps(data, default=str)

    def export_console(self) -> str:
        """Export spans in human-readable format."""
        lines = []
        
        with self._lock:
            # Group by trace
            traces: Dict[str, List[Span]] = {}
            for span in self._spans.values():
                if span.trace_id not in traces:
                    traces[span.trace_id] = []
                traces[span.trace_id].append(span)

            for trace_id, spans in traces.items():
                lines.append(f"\n=== Trace {trace_id} ===")
                # Sort by start time and depth
                spans_sorted = sorted(spans, key=lambda s: (s.start_time, s.parent_span_id or ''))
                
                for span in spans_sorted:
                    indent = "  " if span.parent_span_id else ""
                    status_emoji = "✓" if span.status == "ok" else "✗"
                    duration = f"{span.duration_ms:.2f}ms" if span.duration_ms else "running"
                    
                    lines.append(
                        f"{indent}{status_emoji} {span.operation_name} "
                        f"({span.span_id[:8]}...) {duration}"
                    )
                    
                    if span.attributes:
                        for k, v in span.attributes.items():
                            lines.append(f"{indent}  @{k}={v}")
                    
                    if span.error_message:
                        lines.append(f"{indent}  ERROR: {span.error_message}")

        return '\n'.join(lines)


# Context variable for current trace context
_trace_context_var: contextvars.ContextVar[Optional[TracingContext]] = \
    contextvars.ContextVar('trace_context', default=None)


def get_tracing_context() -> TracingContext:
    """Get or create current tracing context."""
    ctx = _trace_context_var.get()
    if ctx is None:
        ctx = TracingContext()
        _trace_context_var.set(ctx)
    return ctx


F = TypeVar('F', bound=Callable[..., Any])


def traced_operation(
    name: Optional[str] = None,
    include_args: bool = False,
    include_result: bool = False,
) -> Callable[[F], F]:
    """Decorator to trace a function as a single operation.
    
    Args:
        name: Optional operation name (defaults to function name)
        include_args: Whether to include function arguments in span attributes
        include_result: Whether to include function result in span attributes
        
    Example:
        @traced_operation(name='process_records')
        def process(records):
            pass
    """
    def decorator(func: F) -> F:
        operation_name = name or func.__name__
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracing_context()
            attributes = {}
            
            if include_args:
                attributes['args'] = str(args)[:100]
                attributes['kwargs'] = str(kwargs)[:100]
            
            span = tracer.start_span(operation_name, attributes=attributes)
            
            try:
                result = func(*args, **kwargs)
                if include_result:
                    attributes['result'] = str(result)[:100]
                tracer.end_span(span.span_id, status='ok')
                return result
            except Exception as e:
                tracer.end_span(
                    span.span_id,
                    status='error',
                    error_message=str(e),
                )
                raise
        
        return wrapper  # type: ignore
    
    return decorator


@functools.lru_cache(maxsize=None)
def parse_traceparent(header: str) -> Dict[str, str]:
    """Parse W3C traceparent header.
    
    Format: version-trace_id-parent_id-trace_flags
    
    Args:
        header: Traceparent header value
        
    Returns:
        Dictionary with trace_id, parent_id, flags
    """
    try:
        parts = header.split('-')
        if len(parts) >= 4:
            return {
                'version': parts[0],
                'trace_id': parts[1],
                'parent_id': parts[2],
                'flags': parts[3],
            }
    except Exception:
        pass
    
    return {}


def inject_traceparent(trace_id: str, span_id: str, sampled: bool = True) -> str:
    """Create a W3C traceparent header.
    
    Args:
        trace_id: Trace ID
        span_id: Span ID (becomes parent ID)
        sampled: Whether trace is sampled
        
    Returns:
        Traceparent header value
    """
    flags = "01" if sampled else "00"
    return f"00-{trace_id}-{span_id}-{flags}"


class ContextPropagator:
    """Handles context propagation across service boundaries."""

    @staticmethod
    def inject_headers(trace_context: TracingContext) -> Dict[str, str]:
        """Inject tracing context into HTTP headers.
        
        Args:
            trace_context: Current tracing context
            
        Returns:
            Dictionary of headers to include in requests
        """
        current_span = trace_context.get_current_span()
        if not current_span:
            return {}

        headers = {}

        # W3C traceparent header
        headers['traceparent'] = inject_traceparent(
            current_span.trace_id,
            current_span.span_id,
        )

        # B3 headers for Kafka/message systems
        headers['x-b3-traceid'] = current_span.trace_id
        headers['x-b3-spanid'] = current_span.span_id
        if current_span.parent_span_id:
            headers['x-b3-parentspanid'] = current_span.parent_span_id

        return headers

    @staticmethod
    def extract_headers(headers: Dict[str, str]) -> Dict[str, str]:
        """Extract tracing context from HTTP headers.
        
        Args:
            headers: Request headers
            
        Returns:
            Dictionary with trace_id and parent_span_id
        """
        context = {}

        # Try W3C traceparent first
        if 'traceparent' in headers:
            parsed = parse_traceparent(headers['traceparent'])
            if parsed:
                context['trace_id'] = parsed.get('trace_id')
                context['parent_span_id'] = parsed.get('parent_id')

        # Fall back to B3 headers
        if not context.get('trace_id'):
            context['trace_id'] = headers.get('x-b3-traceid')
        if not context.get('parent_span_id'):
            context['parent_span_id'] = headers.get('x-b3-parentspanid')

        return {k: v for k, v in context.items() if v}
