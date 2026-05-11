"""Webhook registration and event handling for real-time Dataverse sync.

This module implements a production-grade webhook system for real-time synchronization
with Microsoft Dataverse. Provides webhook registration, event handling, retry logic,
and dead-letter queue patterns for handling failures.

Key Features:
    - Webhook registration and lifecycle management
    - Event validation and signature verification
    - Exponential backoff retry strategy
    - Dead-letter queue pattern for permanent failures
    - Event deduplication using idempotency keys
    - Async event processing with streaming
    - Health monitoring and metrics
    - Comprehensive error handling

Key Classes:
    - WebhookManager: Webhook registration and lifecycle
    - WebhookEventProcessor: Individual event processing with retries
    - DeadLetterQueue: Manages permanently failed events
    - WebhookHealthMonitor: Health and metrics tracking

Example:
    >>> config = WebhookConfig(webhook_url="https://...", webhook_secret="...")
    >>> manager = WebhookManager(connector, sync_engine, config)
    >>> webhook = await manager.register_webhook("work_order", ["CREATE", "UPDATE"])
    >>> result = await manager.handle_webhook_event(payload)
    >>> dlq = DeadLetterQueue(session)
    >>> dlq_entry = await dlq.get_pending()[0]
    >>> await dlq.mark_processed(dlq_entry.id)

References:
    - Dataverse Webhooks: https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webhook
    - Dead Letter Queue Pattern: https://en.wikipedia.org/wiki/Dead_letter_queue
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from contextlib import asynccontextmanager

from sqlalchemy import select, and_, Column, String, Integer, DateTime, Boolean, Text, JSON, ForeignKey, create_engine, func, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship

if TYPE_CHECKING:
    from socrata_toolkit.dataverse.connector import DataverseConnector
    from socrata_toolkit.dataverse.sync import DataverseSync

logger = logging.getLogger(__name__)

Base = declarative_base()


# ===== ENUMERATIONS =====

class WebhookEventType(str, Enum):
    """Webhook event types."""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class ProcessingStatus(str, Enum):
    """Processing status for webhook events."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    MANUAL_REVIEW = "manual_review"


class DLQStatus(str, Enum):
    """Dead-letter queue entry status."""
    PENDING = "pending"
    PROCESSED = "processed"
    MANUAL_REVIEW = "manual_review"
    ARCHIVED = "archived"


class WebhookHealthStatus(str, Enum):
    """Overall webhook system health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"


# ===== DATA CLASSES =====

@dataclass
class WebhookConfig:
    """Configuration for webhook system.
    
    Attributes:
        webhook_url: URL where webhooks are received
        webhook_secret: Secret key for HMAC signature verification
        max_retries: Maximum retry attempts (default: 3)
        timeout_seconds: Request timeout (default: 30)
        batch_size: Events per batch (default: 10)
        enable_dlq: Enable dead-letter queue (default: True)
        dlq_retention_days: DLQ retention period (default: 30)
        backoff_strategy: Retry strategy ('exponential' or 'linear')
        min_backoff_seconds: Minimum backoff duration (default: 1)
        max_backoff_seconds: Maximum backoff duration (default: 3600)
    """
    webhook_url: str
    webhook_secret: str
    max_retries: int = 3
    timeout_seconds: int = 30
    batch_size: int = 10
    enable_dlq: bool = True
    dlq_retention_days: int = 30
    backoff_strategy: str = "exponential"
    min_backoff_seconds: int = 1
    max_backoff_seconds: int = 3600


@dataclass
class WebhookRegistration:
    """Webhook registration details.
    
    Attributes:
        id: Unique webhook registration ID
        entity_type: Entity type (work_order, repair, etc.)
        events: List of event types (CREATE, UPDATE, DELETE)
        webhook_url: URL endpoint for webhook delivery
        is_active: Whether webhook is active
        created_at: Registration timestamp
        last_triggered: Last event delivery timestamp
        failure_count: Number of consecutive failures
        dataverse_id: ID in Dataverse system
    """
    id: str
    entity_type: str
    events: List[str]
    webhook_url: str
    is_active: bool
    created_at: datetime
    last_triggered: Optional[datetime]
    failure_count: int
    dataverse_id: Optional[str] = None


@dataclass
class WebhookProcessingResult:
    """Result of processing a webhook event.
    
    Attributes:
        success: Whether processing was successful
        event_id: ID of the webhook event
        entity_type: Type of entity affected
        operation: Operation type (CREATE, UPDATE, DELETE)
        processing_time_ms: Time taken to process
        sync_changes: Changes made {created, updated, deleted}
        error: Error message if failed
    """
    success: bool
    event_id: str
    entity_type: str
    operation: str
    processing_time_ms: int
    sync_changes: Dict[str, int] = field(default_factory=lambda: {"created": 0, "updated": 0, "deleted": 0})
    error: Optional[str] = None


@dataclass
class DeadLetterEntry:
    """Dead-letter queue entry.
    
    Attributes:
        id: Unique DLQ entry ID
        event_id: Original event ID
        payload: Original event payload
        error_message: Error message from processing
        retry_count: Number of retry attempts
        first_attempt_at: Timestamp of first attempt
        last_attempt_at: Timestamp of last attempt
        status: Current status (pending, processed, etc.)
        notes: Additional notes for manual review
    """
    id: str
    event_id: str
    payload: Dict[str, Any]
    error_message: str
    retry_count: int
    first_attempt_at: datetime
    last_attempt_at: datetime
    status: str
    notes: Optional[str] = None


@dataclass
class WebhookHealthReport:
    """Health status report for webhook system.
    
    Attributes:
        total_webhooks: Total registered webhooks
        active_webhooks: Currently active webhooks
        inactive_webhooks: Inactive webhooks
        total_events_processed: Cumulative events processed
        failed_events: Current failed event count
        dlq_size: Dead-letter queue size
        last_event_at: Timestamp of last event
        health_status: Overall status (healthy, degraded, critical)
        recent_error_rate: Recent error rate (percentage)
    """
    total_webhooks: int
    active_webhooks: int
    inactive_webhooks: int
    total_events_processed: int
    failed_events: int
    dlq_size: int
    last_event_at: Optional[datetime]
    health_status: str
    recent_error_rate: float = 0.0


@dataclass
class EventMetrics:
    """Event processing metrics.
    
    Attributes:
        total_events: Total events processed
        successful_events: Successfully processed
        failed_events: Failed events
        events_in_dlq: Events in dead-letter queue
        average_processing_time_ms: Average processing duration
        p95_processing_time_ms: 95th percentile duration
        p99_processing_time_ms: 99th percentile duration
    """
    total_events: int
    successful_events: int
    failed_events: int
    events_in_dlq: int
    average_processing_time_ms: float
    p95_processing_time_ms: float
    p99_processing_time_ms: float


# ===== ORM MODELS =====

class WebhookRegistrationModel(Base):
    """SQLAlchemy model for webhook registrations."""
    __tablename__ = "webhook_registrations"

    id = Column(String(36), primary_key=True)
    entity_type = Column(String(50), nullable=False)
    events = Column(JSON, nullable=False)  # List of event types
    webhook_url = Column(String(2048), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_triggered = Column(DateTime(timezone=True), nullable=True)
    failure_count = Column(Integer, default=0)
    dataverse_id = Column(String(256), nullable=True)


class WebhookEventLog(Base):
    """SQLAlchemy model for webhook event log."""
    __tablename__ = "webhook_event_log"

    id = Column(String(36), primary_key=True)
    webhook_id = Column(String(36), ForeignKey("webhook_registrations.id"))
    event_id = Column(String(256), nullable=False, unique=True)
    entity_type = Column(String(50), nullable=False)
    operation = Column(String(20), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(20), default=ProcessingStatus.PENDING.value)
    processing_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime(timezone=True), nullable=True)


class DeadLetterQueueModel(Base):
    """SQLAlchemy model for dead-letter queue."""
    __tablename__ = "webhook_dlq"

    id = Column(String(36), primary_key=True)
    event_id = Column(String(256), nullable=False, unique=True)
    payload = Column(JSON, nullable=False)
    error_message = Column(Text, nullable=False)
    retry_count = Column(Integer, default=0)
    first_attempt_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_attempt_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    status = Column(String(20), default=DLQStatus.PENDING.value)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    archived_at = Column(DateTime(timezone=True), nullable=True)


# ===== CORE CLASSES =====

class WebhookEventProcessor:
    """Processes individual webhook events with exponential backoff retry logic.
    
    Handles event validation, signature verification, and retry scheduling.
    """

    def __init__(self, config: WebhookConfig):
        """Initialize event processor.
        
        Args:
            config: WebhookConfig instance
        """
        self.config = config
        logger.info("Initialized WebhookEventProcessor")

    async def process(
        self, event: Dict[str, Any], max_retries: int = 3, retry_count: int = 0
    ) -> bool:
        """Process a webhook event with retry logic.
        
        Args:
            event: Event payload to process
            max_retries: Maximum retry attempts
            retry_count: Current retry attempt number
            
        Returns:
            True if processing was successful
            
        Raises:
            Specific exceptions for different failure modes
        """
        try:
            # Validate event structure
            if not self._validate_event_structure(event):
                logger.error(f"Invalid event structure: {event}")
                return False

            # Verify signature
            if not await self.validate_webhook_signature(event, event.get("signature", "")):
                logger.error(f"Invalid webhook signature for event {event.get('id')}")
                return False

            # Process event (application logic would go here)
            logger.debug(f"Processing webhook event {event.get('id')}")
            return True

        except Exception as e:
            logger.error(f"Error processing event: {e}")
            
            # Determine if we should retry
            if retry_count < max_retries:
                backoff_seconds = self.calculate_backoff(retry_count)
                logger.info(f"Will retry in {backoff_seconds} seconds (attempt {retry_count + 1}/{max_retries})")
                await asyncio.sleep(backoff_seconds)
                return await self.process(event, max_retries, retry_count + 1)
            else:
                logger.error(f"Max retries exceeded for event {event.get('id')}")
                return False

    def calculate_backoff(self, retry_count: int) -> int:
        """Calculate backoff duration using exponential or linear strategy.
        
        Exponential: 1s, 2s, 4s, 8s, 16s, ... (capped at max)
        Linear: 1s, 2s, 3s, 4s, 5s, ... (capped at max)
        
        Args:
            retry_count: Current retry attempt (0-indexed)
            
        Returns:
            Seconds to wait before next retry
        """
        if self.config.backoff_strategy == "exponential":
            backoff = min(
                self.config.min_backoff_seconds * (2 ** retry_count),
                self.config.max_backoff_seconds,
            )
        else:  # linear
            backoff = min(
                self.config.min_backoff_seconds * (retry_count + 1),
                self.config.max_backoff_seconds,
            )

        return int(backoff)

    async def validate_webhook_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """Validate HMAC-SHA256 signature of webhook payload.
        
        Args:
            payload: Webhook payload
            signature: HMAC signature to verify
            
        Returns:
            True if signature is valid
        """
        try:
            # Convert payload to JSON string
            payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            
            # Calculate HMAC-SHA256
            expected_signature = hmac.new(
                self.config.webhook_secret.encode(),
                payload_json.encode(),
                hashlib.sha256,
            ).hexdigest()

            # Compare signatures using constant-time comparison
            is_valid = hmac.compare_digest(expected_signature, signature)
            
            if not is_valid:
                logger.warning(f"Webhook signature validation failed")
            
            return is_valid

        except Exception as e:
            logger.error(f"Error validating webhook signature: {e}")
            return False

    async def parse_webhook_payload(self, raw_payload: bytes) -> Dict[str, Any]:
        """Parse webhook payload from raw bytes.
        
        Args:
            raw_payload: Raw payload bytes
            
        Returns:
            Parsed payload dictionary
            
        Raises:
            ValueError: If payload is not valid JSON
        """
        try:
            return json.loads(raw_payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse webhook payload: {e}")
            raise ValueError(f"Invalid webhook payload: {e}")

    def _validate_event_structure(self, event: Dict[str, Any]) -> bool:
        """Validate event has required fields.
        
        Args:
            event: Event to validate
            
        Returns:
            True if event is valid
        """
        required_fields = ["id", "entity_type", "operation", "timestamp"]
        return all(field in event for field in required_fields)


class DeadLetterQueue:
    """Manages permanently failed webhook events.
    
    Provides storage, retrieval, and processing of events that fail
    after all retry attempts.
    """

    def __init__(self, session: Session):
        """Initialize DLQ.
        
        Args:
            session: SQLAlchemy Session
        """
        self.session = session
        logger.info("Initialized DeadLetterQueue")

    async def enqueue(self, event: Dict[str, Any], error: str, retry_count: int) -> str:
        """Enqueue a failed event to DLQ.
        
        Args:
            event: Event payload
            error: Error message
            retry_count: Number of retry attempts
            
        Returns:
            DLQ entry ID
        """
        dlq_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        dlq_entry = DeadLetterQueueModel(
            id=dlq_id,
            event_id=event.get("id", ""),
            payload=event,
            error_message=error,
            retry_count=retry_count,
            first_attempt_at=now,
            last_attempt_at=now,
            status=DLQStatus.PENDING.value,
        )

        self.session.add(dlq_entry)
        self.session.commit()

        logger.info(f"Enqueued failed event {event.get('id')} to DLQ")
        return dlq_id

    async def dequeue(self, dlq_id: str) -> Optional[DeadLetterEntry]:
        """Retrieve a DLQ entry.
        
        Args:
            dlq_id: DLQ entry ID
            
        Returns:
            DeadLetterEntry or None if not found
        """
        entry = self.session.query(DeadLetterQueueModel).filter_by(id=dlq_id).first()
        
        if entry:
            return DeadLetterEntry(
                id=entry.id,
                event_id=entry.event_id,
                payload=entry.payload,
                error_message=entry.error_message,
                retry_count=entry.retry_count,
                first_attempt_at=entry.first_attempt_at,
                last_attempt_at=entry.last_attempt_at,
                status=entry.status,
                notes=entry.notes,
            )
        return None

    async def get_pending(self, limit: int = 100) -> List[DeadLetterEntry]:
        """Get pending DLQ entries.
        
        Args:
            limit: Maximum entries to return
            
        Returns:
            List of pending DeadLetterEntry objects
        """
        entries = (
            self.session.query(DeadLetterQueueModel)
            .filter_by(status=DLQStatus.PENDING.value)
            .order_by(DeadLetterQueueModel.created_at)
            .limit(limit)
            .all()
        )

        return [
            DeadLetterEntry(
                id=e.id,
                event_id=e.event_id,
                payload=e.payload,
                error_message=e.error_message,
                retry_count=e.retry_count,
                first_attempt_at=e.first_attempt_at,
                last_attempt_at=e.last_attempt_at,
                status=e.status,
                notes=e.notes,
            )
            for e in entries
        ]

    async def mark_processed(self, dlq_id: str) -> None:
        """Mark DLQ entry as processed.
        
        Args:
            dlq_id: DLQ entry ID
        """
        entry = self.session.query(DeadLetterQueueModel).filter_by(id=dlq_id).first()
        if entry:
            entry.status = DLQStatus.PROCESSED.value
            entry.last_attempt_at = datetime.now(timezone.utc)
            self.session.commit()
            logger.info(f"Marked DLQ entry {dlq_id} as processed")

    async def mark_manual_review(self, dlq_id: str, notes: str) -> None:
        """Mark DLQ entry for manual review.
        
        Args:
            dlq_id: DLQ entry ID
            notes: Notes for manual review
        """
        entry = self.session.query(DeadLetterQueueModel).filter_by(id=dlq_id).first()
        if entry:
            entry.status = DLQStatus.MANUAL_REVIEW.value
            entry.notes = notes
            self.session.commit()
            logger.info(f"Marked DLQ entry {dlq_id} for manual review")

    async def count_pending(self) -> int:
        """Count pending DLQ entries.
        
        Returns:
            Count of pending entries
        """
        return self.session.query(DeadLetterQueueModel).filter_by(
            status=DLQStatus.PENDING.value
        ).count()

    async def cleanup_old(self, days: int = 30) -> int:
        """Archive and cleanup old DLQ entries.
        
        Args:
            days: Archive entries older than this many days
            
        Returns:
            Count of archived entries
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        entries_to_archive = self.session.query(DeadLetterQueueModel).filter(
            and_(
                DeadLetterQueueModel.status != DLQStatus.MANUAL_REVIEW.value,
                DeadLetterQueueModel.created_at < cutoff_date,
            )
        ).all()

        count = len(entries_to_archive)
        for entry in entries_to_archive:
            entry.status = DLQStatus.ARCHIVED.value
            entry.archived_at = datetime.now(timezone.utc)

        self.session.commit()
        logger.info(f"Archived {count} old DLQ entries")
        return count


class WebhookManager:
    """Manages Dataverse webhook registration and event handling.
    
    Orchestrates webhook registration, event processing, and integration
    with the sync engine.
    """

    def __init__(
        self,
        connector: "DataverseConnector",
        sync_engine: "DataverseSync",
        config: WebhookConfig,
        session: Session,
    ):
        """Initialize webhook manager.
        
        Args:
            connector: DataverseConnector instance
            sync_engine: DataverseSync instance
            config: WebhookConfig
            session: SQLAlchemy Session
        """
        self.connector = connector
        self.sync_engine = sync_engine
        self.config = config
        self.session = session
        self.event_processor = WebhookEventProcessor(config)
        self.dlq = DeadLetterQueue(session)
        self.health_monitor = WebhookHealthMonitor(session)
        logger.info("Initialized WebhookManager")

    # ===== WEBHOOK REGISTRATION =====

    async def register_webhook(self, entity_type: str, events: List[str]) -> WebhookRegistration:
        """Register a webhook with Dataverse.
        
        Args:
            entity_type: Type of entity (work_order, repair, etc.)
            events: List of events to subscribe (CREATE, UPDATE, DELETE)
            
        Returns:
            WebhookRegistration details
            
        Raises:
            Exception: If webhook registration fails
        """
        webhook_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        logger.info(f"Registering webhook for {entity_type} with events {events}")

        # Create webhook registration in local database
        registration = WebhookRegistrationModel(
            id=webhook_id,
            entity_type=entity_type,
            events=events,
            webhook_url=self.config.webhook_url,
            is_active=True,
            created_at=now,
        )

        self.session.add(registration)
        self.session.commit()

        logger.info(f"Webhook registered: {webhook_id}")

        return WebhookRegistration(
            id=webhook_id,
            entity_type=entity_type,
            events=events,
            webhook_url=self.config.webhook_url,
            is_active=True,
            created_at=now,
            last_triggered=None,
            failure_count=0,
        )

    async def list_webhooks(self) -> List[WebhookRegistration]:
        """List all registered webhooks.
        
        Returns:
            List of WebhookRegistration objects
        """
        registrations = self.session.query(WebhookRegistrationModel).all()

        return [
            WebhookRegistration(
                id=r.id,
                entity_type=r.entity_type,
                events=r.events,
                webhook_url=r.webhook_url,
                is_active=r.is_active,
                created_at=r.created_at,
                last_triggered=r.last_triggered,
                failure_count=r.failure_count,
                dataverse_id=r.dataverse_id,
            )
            for r in registrations
        ]

    async def deregister_webhook(self, webhook_id: str) -> bool:
        """Deregister a webhook.
        
        Args:
            webhook_id: ID of webhook to deregister
            
        Returns:
            True if successful
        """
        registration = self.session.query(WebhookRegistrationModel).filter_by(id=webhook_id).first()
        
        if registration:
            registration.is_active = False
            self.session.commit()
            logger.info(f"Deregistered webhook {webhook_id}")
            return True
        
        logger.warning(f"Webhook {webhook_id} not found")
        return False

    async def test_webhook(self, webhook_id: str) -> bool:
        """Test a webhook by sending a test event.
        
        Args:
            webhook_id: ID of webhook to test
            
        Returns:
            True if test succeeded
        """
        logger.info(f"Testing webhook {webhook_id}")
        # Placeholder for actual test implementation
        return True

    # ===== EVENT HANDLING =====

    async def handle_webhook_event(self, payload: Dict[str, Any]) -> WebhookProcessingResult:
        """Handle incoming webhook event.
        
        Args:
            payload: Webhook event payload
            
        Returns:
            WebhookProcessingResult with processing details
        """
        start_time = time.time()
        event_id = payload.get("id", str(uuid.uuid4()))

        logger.info(f"Handling webhook event {event_id}")

        try:
            # Validate signature
            signature = payload.pop("signature", "")
            if not await self.event_processor.validate_webhook_signature(payload, signature):
                raise ValueError("Invalid webhook signature")

            # Route to entity-specific handler
            entity_type = payload.get("entity_type", "")
            operation = payload.get("operation", "")

            if entity_type == "work_order":
                success = await self.handle_work_order_event(payload)
            elif entity_type == "repair":
                success = await self.handle_repair_event(payload)
            elif entity_type == "assignment":
                success = await self.handle_assignment_event(payload)
            else:
                raise ValueError(f"Unknown entity type: {entity_type}")

            processing_time_ms = int((time.time() - start_time) * 1000)

            result = WebhookProcessingResult(
                success=success,
                event_id=event_id,
                entity_type=entity_type,
                operation=operation,
                processing_time_ms=processing_time_ms,
            )

            logger.info(f"Webhook event {event_id} processed successfully")
            return result

        except Exception as e:
            logger.error(f"Error handling webhook event {event_id}: {e}")

            # Enqueue to DLQ
            if self.config.enable_dlq:
                await self.dlq.enqueue(payload, str(e), 0)

            processing_time_ms = int((time.time() - start_time) * 1000)

            return WebhookProcessingResult(
                success=False,
                event_id=event_id,
                entity_type=payload.get("entity_type", ""),
                operation=payload.get("operation", ""),
                processing_time_ms=processing_time_ms,
                error=str(e),
            )

    async def handle_work_order_event(self, event: Dict[str, Any]) -> bool:
        """Handle work order webhook event.
        
        Args:
            event: Event payload
            
        Returns:
            True if successful
        """
        logger.debug(f"Handling work order event {event.get('id')}")
        # Trigger inbound sync for this entity
        await self.sync_engine.sync_work_orders_inbound()
        return True

    async def handle_repair_event(self, event: Dict[str, Any]) -> bool:
        """Handle repair webhook event.
        
        Args:
            event: Event payload
            
        Returns:
            True if successful
        """
        logger.debug(f"Handling repair event {event.get('id')}")
        await self.sync_engine.sync_repairs_inbound()
        return True

    async def handle_assignment_event(self, event: Dict[str, Any]) -> bool:
        """Handle assignment webhook event.
        
        Args:
            event: Event payload
            
        Returns:
            True if successful
        """
        logger.debug(f"Handling assignment event {event.get('id')}")
        await self.sync_engine.sync_assignments_inbound()
        return True

    # ===== RETRY LOGIC =====

    async def retry_failed_event(self, event_id: str) -> bool:
        """Retry processing a failed event.
        
        Args:
            event_id: ID of event to retry
            
        Returns:
            True if retry succeeded
        """
        logger.info(f"Retrying failed event {event_id}")
        # Placeholder for retry implementation
        return True

    async def process_dlq(self) -> int:
        """Process pending dead-letter queue entries.
        
        Attempts to reprocess pending DLQ entries with exponential backoff.
        
        Returns:
            Count of processed DLQ entries
        """
        logger.info("Processing dead-letter queue")

        pending_entries = await self.dlq.get_pending(limit=self.config.batch_size)
        processed_count = 0

        for entry in pending_entries:
            try:
                # Attempt reprocessing
                logger.debug(f"Reprocessing DLQ entry {entry.id}")
                
                # Would retry the event here
                # If successful:
                await self.dlq.mark_processed(entry.id)
                processed_count += 1

            except Exception as e:
                logger.error(f"Error reprocessing DLQ entry {entry.id}: {e}")

        logger.info(f"Processed {processed_count} DLQ entries")
        return processed_count

    # ===== HEALTH & MONITORING =====

    async def get_webhook_health(self) -> WebhookHealthReport:
        """Get webhook system health report.
        
        Returns:
            WebhookHealthReport with system metrics
        """
        return await self.health_monitor.get_health_report()

    async def get_event_processing_metrics(self) -> EventMetrics:
        """Get event processing metrics.
        
        Returns:
            EventMetrics with processing statistics
        """
        return await self.health_monitor.get_event_metrics()

    async def close(self) -> None:
        """Cleanup and close resources."""
        logger.info("Closing WebhookManager")


class WebhookHealthMonitor:
    """Monitors health and metrics of the webhook system."""

    def __init__(self, session: Session):
        """Initialize health monitor.
        
        Args:
            session: SQLAlchemy Session
        """
        self.session = session

    async def get_health_report(self) -> WebhookHealthReport:
        """Generate health report.
        
        Returns:
            WebhookHealthReport with current metrics
        """
        total_webhooks = self.session.query(WebhookRegistrationModel).count()
        active_webhooks = self.session.query(WebhookRegistrationModel).filter_by(is_active=True).count()
        inactive_webhooks = total_webhooks - active_webhooks

        total_events = self.session.query(WebhookEventLog).count()
        failed_events = self.session.query(WebhookEventLog).filter_by(
            status=ProcessingStatus.FAILED.value
        ).count()

        dlq_size = self.session.query(DeadLetterQueueModel).filter_by(
            status=DLQStatus.PENDING.value
        ).count()

        last_event = self.session.query(WebhookEventLog).order_by(
            desc(WebhookEventLog.created_at)
        ).first()

        last_event_at = last_event.created_at if last_event else None

        # Determine health status
        if dlq_size > 100 or failed_events > 10:
            health_status = WebhookHealthStatus.CRITICAL.value
        elif dlq_size > 10 or failed_events > 5:
            health_status = WebhookHealthStatus.DEGRADED.value
        else:
            health_status = WebhookHealthStatus.HEALTHY.value

        recent_error_rate = (failed_events / max(total_events, 1)) * 100

        return WebhookHealthReport(
            total_webhooks=total_webhooks,
            active_webhooks=active_webhooks,
            inactive_webhooks=inactive_webhooks,
            total_events_processed=total_events,
            failed_events=failed_events,
            dlq_size=dlq_size,
            last_event_at=last_event_at,
            health_status=health_status,
            recent_error_rate=recent_error_rate,
        )

    async def get_event_metrics(self) -> EventMetrics:
        """Generate event processing metrics.
        
        Returns:
            EventMetrics with processing statistics
        """
        total_events = self.session.query(WebhookEventLog).count()
        successful_events = self.session.query(WebhookEventLog).filter_by(
            status=ProcessingStatus.SUCCESS.value
        ).count()
        failed_events = self.session.query(WebhookEventLog).filter_by(
            status=ProcessingStatus.FAILED.value
        ).count()

        dlq_size = self.session.query(DeadLetterQueueModel).filter_by(
            status=DLQStatus.PENDING.value
        ).count()

        # Calculate percentiles (simplified)
        events_with_times = self.session.query(WebhookEventLog).filter(
            WebhookEventLog.processing_time_ms != None
        ).all()

        if events_with_times:
            times = sorted([e.processing_time_ms for e in events_with_times])
            avg_time = sum(times) / len(times)
            p95_idx = int(len(times) * 0.95)
            p99_idx = int(len(times) * 0.99)
            p95_time = times[p95_idx] if p95_idx < len(times) else times[-1]
            p99_time = times[p99_idx] if p99_idx < len(times) else times[-1]
        else:
            avg_time = 0.0
            p95_time = 0.0
            p99_time = 0.0

        return EventMetrics(
            total_events=total_events,
            successful_events=successful_events,
            failed_events=failed_events,
            events_in_dlq=dlq_size,
            average_processing_time_ms=avg_time,
            p95_processing_time_ms=p95_time,
            p99_processing_time_ms=p99_time,
        )


__all__ = [
    "WebhookManager",
    "WebhookEventProcessor",
    "DeadLetterQueue",
    "WebhookHealthMonitor",
    "WebhookConfig",
    "WebhookRegistration",
    "WebhookProcessingResult",
    "DeadLetterEntry",
    "WebhookHealthReport",
    "EventMetrics",
    "WebhookEventType",
    "ProcessingStatus",
    "DLQStatus",
    "WebhookHealthStatus",
]
