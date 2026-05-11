"""Structured logging for observability and event tracking."""
from typing import Any, Dict, List

__all__ = ["StructuredLogger", "get_event_log"]


class StructuredLogger:
    """Structured logger for emitting observable events."""

    def __init__(self) -> None:
        """Initialize the StructuredLogger."""
        self.events: List[Dict[str, Any]] = []

    def log_event(self, event_name: str, metadata: Dict[str, Any]) -> None:
        """Log a structured event.
        
        Args:
            event_name: Name of the event
            metadata: Event metadata dictionary
        """
        event = {"event_name": event_name, "metadata": metadata}
        self.events.append(event)


def get_event_log() -> List[Dict[str, Any]]:
    """Get the event log.
    
    Returns:
        List of logged events
    """
    return []
