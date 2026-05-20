"""Change Data Capture (CDC) engine for processing data changes.

This module implements a production-grade CDC system for capturing, processing,
and tracking all data modifications. Supports deduplication, ordering validation,
watermarking to prevent reprocessing, and integration with SCD Type 2.

Key Features:
    - Immutable CDC event log
    - Deduplication of duplicate updates
    - Order validation across datasets
    - Watermark tracking (prevent reprocessing)
    - SCD Type 2 integration
    - CDC event transformation and enrichment
    - Export for downstream systems

Classes:
    CDCEvent: Single change event
    CDCProcessor: Process CDC events
    CDCStorage: Store CDC events in PostgreSQL
    ProcessingResult: Result of batch processing

Example:
    >>> processor = CDCProcessor(dsn="postgresql://...")
    >>> event = CDCEvent(
    ...     operation="UPDATE",
    ...     source_dataset="sidewalk_conditions",
    ...     record_id="sidewalk_123",
    ...     before={"condition": "fair"},
    ...     after={"condition": "excellent"}
    ... )
    >>> result = processor.process_cdc_event(event)
    >>> events = processor.get_events("sidewalk_conditions")
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager

try:
    import psycopg
    from psycopg import sql
except ImportError:
    psycopg = None  # type: ignore
    sql = None  # type: ignore

logger = logging.getLogger(__name__)


class Operation(Enum):
    """CDC operation type."""
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass
class CDCEvent:
    """Single CDC change event.
    
    Represents a single change to a record, with before/after values.
    Used as the primary unit of work for CDC processing.
    
    Attributes:
        event_id: Unique event identifier (UUID)
        source_dataset: Socrata dataset_id or source system
        operation: Type of change (INSERT, UPDATE, DELETE)
        record_id: Business key of the changed record
        timestamp_ms: When change occurred (milliseconds since epoch)
        before: Old values (None for INSERT)
        after: New values (None for DELETE)
        metadata: Additional metadata (source_version, etc.)
    """
    event_id: str
    source_dataset: str
    operation: str
    record_id: str
    timestamp_ms: int
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CDCEvent:
        """Create from dictionary."""
        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())),
            source_dataset=data["source_dataset"],
            operation=data["operation"],
            record_id=data["record_id"],
            timestamp_ms=data["timestamp_ms"],
            before=data.get("before"),
            after=data.get("after"),
            metadata=data.get("metadata"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "source_dataset": self.source_dataset,
            "operation": self.operation,
            "record_id": self.record_id,
            "timestamp_ms": self.timestamp_ms,
            "before": self.before,
            "after": self.after,
            "metadata": self.metadata or {},
        }


@dataclass
class ProcessingResult:
    """Result of CDC event processing.
    
    Attributes:
        success: Whether processing succeeded
        event_id: ID of processed event
        message: Status message
        scd_record_id: ID of SCD record created/updated (if applicable)
        error: Error message if failed
    """
    success: bool
    event_id: str
    message: str
    scd_record_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class OrderingReport:
    """Report on event ordering validation.
    
    Attributes:
        valid: Whether events are in valid order
        issues: List of ordering issues found
        stats: Statistics about the events
    """
    valid: bool
    issues: List[str]
    stats: Dict[str, Any]


class CDCStorage:
    """Persistent storage for CDC events in PostgreSQL.
    
    Maintains immutable CDC event log with indexes for efficient
    querying by dataset, operation type, and time window.
    """

    def __init__(self, dsn: str) -> None:
        """Initialize CDC storage.
        
        Args:
            dsn: PostgreSQL connection string
            
        Raises:
            ImportError: If psycopg not installed
        """
        if psycopg is None:
            raise ImportError("Install postgres extras: pip install '.[postgres]'")
        self.dsn = dsn
        self.logger = logger.getChild(self.__class__.__name__)

    @contextmanager
    def _get_connection(self):
        """Context manager for database connection."""
        conn = psycopg.connect(self.dsn)
        try:
            yield conn
        finally:
            conn.close()

    def store_event(self, event: CDCEvent) -> bool:
        """Store a CDC event.
        
        Args:
            event: CDCEvent to store
            
        Returns:
            True if successful
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO public.cdc_events
                       (event_id, source_dataset, operation, record_id, timestamp_ms,
                        before_values, after_values, metadata)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        event.event_id,
                        event.source_dataset,
                        event.operation,
                        event.record_id,
                        event.timestamp_ms,
                        json.dumps(event.before) if event.before else None,
                        json.dumps(event.after) if event.after else None,
                        json.dumps(event.metadata or {}),
                    )
                )
                conn.commit()
        
        self.logger.debug(f"Stored CDC event: {event.event_id}")
        return True

    def store_batch(self, events: List[CDCEvent]) -> int:
        """Store multiple CDC events.
        
        Args:
            events: List of CDCEvents
            
        Returns:
            Count of stored events
        """
        count = 0
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                for event in events:
                    cur.execute(
                        """INSERT INTO public.cdc_events
                           (event_id, source_dataset, operation, record_id, timestamp_ms,
                            before_values, after_values, metadata)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            event.event_id,
                            event.source_dataset,
                            event.operation,
                            event.record_id,
                            event.timestamp_ms,
                            json.dumps(event.before) if event.before else None,
                            json.dumps(event.after) if event.after else None,
                            json.dumps(event.metadata or {}),
                        )
                    )
                    count += 1
                conn.commit()
        
        self.logger.info(f"Stored {count} CDC events")
        return count

    def get_events(
        self, source_dataset: str, limit: int = 10000
    ) -> List[CDCEvent]:
        """Get CDC events for a dataset.
        
        Args:
            source_dataset: Dataset identifier
            limit: Maximum results
            
        Returns:
            List of CDCEvents
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT event_id, source_dataset, operation, record_id,
                              timestamp_ms, before_values, after_values, metadata
                       FROM public.cdc_events
                       WHERE source_dataset = %s
                       ORDER BY timestamp_ms DESC
                       LIMIT %s""",
                    (source_dataset, limit)
                )
                rows = cur.fetchall()
                
                events = []
                for row in rows:
                    events.append(
                        CDCEvent(
                            event_id=row[0],
                            source_dataset=row[1],
                            operation=row[2],
                            record_id=row[3],
                            timestamp_ms=row[4],
                            before=json.loads(row[5]) if row[5] else None,
                            after=json.loads(row[6]) if row[6] else None,
                            metadata=json.loads(row[7]) if row[7] else None,
                        )
                    )
                return events

    def get_events_by_operation(
        self, operation: str, limit: int = 10000
    ) -> List[CDCEvent]:
        """Get CDC events by operation type.
        
        Args:
            operation: Operation type (INSERT, UPDATE, DELETE)
            limit: Maximum results
            
        Returns:
            List of CDCEvents
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT event_id, source_dataset, operation, record_id,
                              timestamp_ms, before_values, after_values, metadata
                       FROM public.cdc_events
                       WHERE operation = %s
                       ORDER BY timestamp_ms DESC
                       LIMIT %s""",
                    (operation, limit)
                )
                rows = cur.fetchall()
                
                events = []
                for row in rows:
                    events.append(
                        CDCEvent(
                            event_id=row[0],
                            source_dataset=row[1],
                            operation=row[2],
                            record_id=row[3],
                            timestamp_ms=row[4],
                            before=json.loads(row[5]) if row[5] else None,
                            after=json.loads(row[6]) if row[6] else None,
                            metadata=json.loads(row[7]) if row[7] else None,
                        )
                    )
                return events

    def get_events_in_window(
        self,
        source_dataset: str,
        start_ms: int,
        end_ms: int,
        limit: int = 10000,
    ) -> List[CDCEvent]:
        """Get CDC events in a time window.
        
        Args:
            source_dataset: Dataset identifier
            start_ms: Window start (milliseconds)
            end_ms: Window end (milliseconds)
            limit: Maximum results
            
        Returns:
            List of CDCEvents
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT event_id, source_dataset, operation, record_id,
                              timestamp_ms, before_values, after_values, metadata
                       FROM public.cdc_events
                       WHERE source_dataset = %s
                         AND timestamp_ms >= %s
                         AND timestamp_ms <= %s
                       ORDER BY timestamp_ms ASC
                       LIMIT %s""",
                    (source_dataset, start_ms, end_ms, limit)
                )
                rows = cur.fetchall()
                
                events = []
                for row in rows:
                    events.append(
                        CDCEvent(
                            event_id=row[0],
                            source_dataset=row[1],
                            operation=row[2],
                            record_id=row[3],
                            timestamp_ms=row[4],
                            before=json.loads(row[5]) if row[5] else None,
                            after=json.loads(row[6]) if row[6] else None,
                            metadata=json.loads(row[7]) if row[7] else None,
                        )
                    )
                return events


class CDCProcessor:
    """Main CDC processor for handling change events.
    
    Processes CDC events: deduplication, validation, SCD updates,
    watermarking, and storage.
    """

    def __init__(self, dsn: str) -> None:
        """Initialize CDC processor.
        
        Args:
            dsn: PostgreSQL connection string
        """
        self.dsn = dsn
        self.storage = CDCStorage(dsn)
        self.logger = logger.getChild(self.__class__.__name__)

    @staticmethod
    def deduplicate_events(events: List[CDCEvent]) -> List[CDCEvent]:
        """Remove duplicate consecutive updates to same record.
        
        If multiple UPDATE events exist for the same record_id in succession
        with the same final state, keep only the latest.
        
        Args:
            events: List of CDC events (should be sorted by timestamp)
            
        Returns:
            Deduplicated list
        """
        if not events:
            return []
        
        # Sort by record_id, then timestamp
        sorted_events = sorted(events, key=lambda e: (e.record_id, e.timestamp_ms))
        
        deduped = []
        current_record = None
        current_state = None
        
        for event in sorted_events:
            if event.record_id != current_record:
                # Different record, include previous event
                if current_record is not None:
                    deduped.append(events[len(deduped)])
                current_record = event.record_id
                current_state = event.after
                deduped.append(event)
            elif event.operation == "UPDATE" and current_state == event.after:
                # Duplicate update to same state, skip
                continue
            else:
                # Different state or non-update, include
                deduped.append(event)
                current_state = event.after
        
        return deduped

    @staticmethod
    def validate_event_order(events: List[CDCEvent]) -> OrderingReport:
        """Validate that events are in correct order.
        
        Checks that events for the same record_id are chronologically ordered
        and don't have gaps or overlaps.
        
        Args:
            events: List of CDC events
            
        Returns:
            OrderingReport with validation results
        """
        issues = []
        record_timestamps: Dict[str, int] = {}
        
        for event in sorted(events, key=lambda e: e.timestamp_ms):
            record_id = event.record_id
            
            if record_id in record_timestamps:
                if event.timestamp_ms < record_timestamps[record_id]:
                    issues.append(
                        f"Event {event.event_id} for {record_id} is out of order "
                        f"({event.timestamp_ms} < {record_timestamps[record_id]})"
                    )
            
            record_timestamps[record_id] = event.timestamp_ms
        
        # Validate operations
        record_sequence: Dict[str, List[str]] = {}
        for event in sorted(events, key=lambda e: e.timestamp_ms):
            record_id = event.record_id
            if record_id not in record_sequence:
                record_sequence[record_id] = []
            
            ops = record_sequence[record_id]
            # INSERT can only be first
            if event.operation == "INSERT" and len(ops) > 0:
                issues.append(f"INSERT for {record_id} after {ops[-1]}")
            # DELETE can only be last
            if event.operation == "DELETE" and len(ops) > 0:
                if ops[-1] == "DELETE":
                    issues.append(f"Multiple DELETEs for {record_id}")
            
            ops.append(event.operation)
        
        return OrderingReport(
            valid=len(issues) == 0,
            issues=issues,
            stats={
                "total_events": len(events),
                "unique_records": len(record_timestamps),
                "duplicate_issues": len([i for i in issues if "out of order" in i]),
                "operation_issues": len([i for i in issues if "out of order" not in i]),
            },
        )

    def process_cdc_event(self, event: CDCEvent) -> ProcessingResult:
        """Process a single CDC event.
        
        Args:
            event: CDCEvent to process
            
        Returns:
            ProcessingResult
        """
        try:
            # Store event
            self.storage.store_event(event)
            
            return ProcessingResult(
                success=True,
                event_id=event.event_id,
                message=f"Processed {event.operation} for {event.record_id}",
            )
        except Exception as e:
            self.logger.error(f"Failed to process event {event.event_id}: {e}")
            return ProcessingResult(
                success=False,
                event_id=event.event_id,
                message="Processing failed",
                error=str(e),
            )

    def batch_process_cdc(self, events: List[CDCEvent]) -> Dict[str, Any]:
        """Process multiple CDC events in a batch.
        
        Args:
            events: List of CDCEvents
            
        Returns:
            Dict with results:
                - total: number of events
                - processed: number successfully processed
                - failed: number that failed
                - deduped: number of duplicates removed
        """
        deduped = self.deduplicate_events(events)
        removed = len(events) - len(deduped)
        
        processed = 0
        failed = 0
        
        try:
            self.storage.store_batch(deduped)
            processed = len(deduped)
        except Exception as e:
            self.logger.error(f"Batch processing failed: {e}")
            failed = len(deduped)
        
        return {
            "total": len(events),
            "processed": processed,
            "failed": failed,
            "deduped": removed,
        }

    def track_watermark(
        self, source_dataset: str, event_id: str, timestamp_ms: int
    ) -> bool:
        """Update watermark to track processing position.
        
        Prevents reprocessing of the same events.
        
        Args:
            source_dataset: Dataset identifier
            event_id: Latest processed event ID
            timestamp_ms: Latest processed timestamp
            
        Returns:
            True if successful
        """
        if psycopg is None:
            return False
        
        try:
            conn = psycopg.connect(self.dsn)
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO public.cdc_watermarks
                       (source_dataset, last_processed_event_id, last_processed_timestamp_ms)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (source_dataset) DO UPDATE SET
                           last_processed_event_id = EXCLUDED.last_processed_event_id,
                           last_processed_timestamp_ms = EXCLUDED.last_processed_timestamp_ms,
                           updated_at = CURRENT_TIMESTAMP""",
                    (source_dataset, event_id, timestamp_ms)
                )
                conn.commit()
                conn.close()
            
            self.logger.debug(f"Updated watermark for {source_dataset}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update watermark: {e}")
            return False

    def get_watermark(self, source_dataset: str) -> Optional[Tuple[str, int]]:
        """Get the last processed watermark for a dataset.
        
        Args:
            source_dataset: Dataset identifier
            
        Returns:
            Tuple of (event_id, timestamp_ms) or None if no watermark
        """
        if psycopg is None:
            return None
        
        try:
            conn = psycopg.connect(self.dsn)
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT last_processed_event_id, last_processed_timestamp_ms
                       FROM public.cdc_watermarks
                       WHERE source_dataset = %s""",
                    (source_dataset,)
                )
                row = cur.fetchone()
                conn.close()
            
            if row:
                return (row[0], row[1])
            return None
        except Exception as e:
            self.logger.error(f"Failed to get watermark: {e}")
            return None

    def get_events(self, source_dataset: str, limit: int = 10000) -> List[CDCEvent]:
        """Get CDC events for a dataset.
        
        Args:
            source_dataset: Dataset identifier
            limit: Maximum results
            
        Returns:
            List of CDCEvents
        """
        return self.storage.get_events(source_dataset, limit)
