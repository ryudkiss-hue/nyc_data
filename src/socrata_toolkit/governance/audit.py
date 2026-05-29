"""Immutable audit trail for compliance and change tracking.

This module provides comprehensive audit logging for all data operations,
supporting regulatory compliance, accountability, and root cause analysis.

Key Features:
    - Immutable audit log (no updates/deletes after insertion)
    - Captures who, what, when, where, why for every change
    - Full before/after value tracking
    - Difference (diff) calculation
    - Correlation with lineage tracking (W3)
    - Export capabilities (CSV, JSON)
    - Compliance reporting

Classes:
    AuditEvent: Single audit log entry
    AuditTrail: Main audit logging interface

Example:
    >>> audit = AuditTrail(dsn="postgresql://...")
    >>> audit.log_update(
    ...     table="sidewalk_conditions",
    ...     entity_id="sidewalk_123",
    ...     old={"condition": "fair"},
    ...     new={"condition": "excellent"},
    ...     user="inspector@nyc.gov",
    ...     reason="Monthly inspection"
    ... )
    >>> events = audit.get_events("sidewalk_conditions", "sidewalk_123")
    >>> report = audit.generate_compliance_report()
"""

from __future__ import annotations

import csv
import json
import logging
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import IO, Any

try:
    import psycopg
    from psycopg import sql
except ImportError:
    psycopg = None  # type: ignore
    sql = None  # type: ignore

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Type of data operation."""
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    TRUNCATE = "TRUNCATE"
    SCHEMA_CHANGE = "SCHEMA_CHANGE"


class ChangeType(Enum):
    """Category of change."""
    DATA_CHANGE = "DATA_CHANGE"
    SCHEMA_CHANGE = "SCHEMA_CHANGE"
    ACCESS = "ACCESS"
    DELETE = "DELETE"
    RESTORE = "RESTORE"


@dataclass
class AuditEvent:
    """Single audit trail event.

    This is an immutable record of a single change, capturing complete provenance
    information for compliance and root cause analysis.

    Attributes:
        audit_id: Unique event identifier (UUID)
        timestamp: When the change occurred (UTC)
        user_name: Who performed the action ('SYSTEM' for automated)
        action: Type of DML operation
        entity_type: Table/entity name
        entity_id: Business key of the record
        change_type: Category of change
        old_values: State before change
        new_values: State after change
        diff: Only the changed fields (for readability)
        reason: Why the change was made (e.g., "monthly_inspection")
        lineage_node_id: Link to W3 lineage node
        correlation_id: Link to W4 observability logs
        ip_address: IP address of the change source
        user_agent: Client user agent
        created_at: Server timestamp when logged
    """
    audit_id: str
    timestamp: datetime
    user_name: str
    action: str  # ActionType value
    entity_type: str
    entity_id: str
    change_type: str  # ChangeType value
    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    diff: dict[str, Any] | None = None
    reason: str | None = None
    lineage_node_id: str | None = None
    correlation_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditEvent:
        """Create from dictionary."""
        return cls(
            audit_id=data["audit_id"],
            timestamp=data["timestamp"],
            user_name=data["user_name"],
            action=data["action"],
            entity_type=data["entity_type"],
            entity_id=data["entity_id"],
            change_type=data["change_type"],
            old_values=data.get("old_values"),
            new_values=data.get("new_values"),
            diff=data.get("diff"),
            reason=data.get("reason"),
            lineage_node_id=data.get("lineage_node_id"),
            correlation_id=data.get("correlation_id"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            created_at=data.get("created_at", datetime.now(timezone.utc)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp.isoformat(),
            "user_name": self.user_name,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "change_type": self.change_type,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "diff": self.diff,
            "reason": self.reason,
            "lineage_node_id": self.lineage_node_id,
            "correlation_id": self.correlation_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat(),
        }


class AuditTrail:
    """Main audit trail interface.

    Provides methods for logging all data operations and querying the
    immutable audit log. The audit trail is append-only and cannot be
    modified after creation (enforced by database rules).
    """

    def __init__(self, dsn: str) -> None:
        """Initialize audit trail.

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

    @staticmethod
    def _calculate_diff(old: dict[str, Any] | None, new: dict[str, Any] | None) -> dict[str, Any]:
        """Calculate difference between old and new values.

        Args:
            old: Before state
            new: After state

        Returns:
            Dict with only changed fields, in format {"field": [old_val, new_val]}
        """
        if old is None:
            old = {}
        if new is None:
            new = {}

        diff = {}
        all_keys = set(old.keys()) | set(new.keys())

        for key in all_keys:
            old_val = old.get(key)
            new_val = new.get(key)
            if old_val != new_val:
                diff[key] = [old_val, new_val]

        return diff

    def log_insert(
        self,
        table: str,
        entity_id: str,
        new_values: dict[str, Any],
        user: str = "SYSTEM",
        reason: str | None = None,
        lineage_node_id: str | None = None,
        correlation_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> str:
        """Log an INSERT operation.

        Args:
            table: Table name
            entity_id: Business key
            new_values: Full record values
            user: User who made change
            reason: Why the change was made
            lineage_node_id: Link to lineage tracking
            correlation_id: Link to observability logs
            ip_address: Source IP
            user_agent: Client user agent

        Returns:
            audit_id of the new event
        """
        audit_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        diff = self._calculate_diff({}, new_values)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO public.audit_trail
                       (audit_id, timestamp, user_name, action, entity_type, entity_id,
                        change_type, old_values, new_values, diff, reason,
                        lineage_node_id, correlation_id, ip_address, user_agent)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        audit_id,
                        now,
                        user,
                        ActionType.INSERT.value,
                        table,
                        entity_id,
                        ChangeType.DATA_CHANGE.value,
                        None,
                        json.dumps(new_values),
                        json.dumps(diff),
                        reason,
                        lineage_node_id,
                        correlation_id,
                        ip_address,
                        user_agent,
                    )
                )
                conn.commit()

        self.logger.info(f"Logged INSERT: {table}/{entity_id} by {user}")
        return audit_id

    def log_update(
        self,
        table: str,
        entity_id: str,
        old: dict[str, Any],
        new: dict[str, Any],
        user: str = "SYSTEM",
        reason: str | None = None,
        lineage_node_id: str | None = None,
        correlation_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> str:
        """Log an UPDATE operation.

        Args:
            table: Table name
            entity_id: Business key
            old: Before state
            new: After state
            user: User who made change
            reason: Why the change was made
            lineage_node_id: Link to lineage tracking
            correlation_id: Link to observability logs
            ip_address: Source IP
            user_agent: Client user agent

        Returns:
            audit_id of the new event
        """
        audit_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        diff = self._calculate_diff(old, new)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO public.audit_trail
                       (audit_id, timestamp, user_name, action, entity_type, entity_id,
                        change_type, old_values, new_values, diff, reason,
                        lineage_node_id, correlation_id, ip_address, user_agent)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        audit_id,
                        now,
                        user,
                        ActionType.UPDATE.value,
                        table,
                        entity_id,
                        ChangeType.DATA_CHANGE.value,
                        json.dumps(old),
                        json.dumps(new),
                        json.dumps(diff),
                        reason,
                        lineage_node_id,
                        correlation_id,
                        ip_address,
                        user_agent,
                    )
                )
                conn.commit()

        self.logger.info(f"Logged UPDATE: {table}/{entity_id} by {user}")
        return audit_id

    def log_delete(
        self,
        table: str,
        entity_id: str,
        old_values: dict[str, Any],
        user: str = "SYSTEM",
        reason: str | None = None,
        lineage_node_id: str | None = None,
        correlation_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> str:
        """Log a DELETE operation.

        Args:
            table: Table name
            entity_id: Business key
            old_values: Full record values before delete
            user: User who made change
            reason: Why the change was made
            lineage_node_id: Link to lineage tracking
            correlation_id: Link to observability logs
            ip_address: Source IP
            user_agent: Client user agent

        Returns:
            audit_id of the new event
        """
        audit_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        diff = self._calculate_diff(old_values, {})

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO public.audit_trail
                       (audit_id, timestamp, user_name, action, entity_type, entity_id,
                        change_type, old_values, new_values, diff, reason,
                        lineage_node_id, correlation_id, ip_address, user_agent)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        audit_id,
                        now,
                        user,
                        ActionType.DELETE.value,
                        table,
                        entity_id,
                        ChangeType.DELETE.value,
                        json.dumps(old_values),
                        None,
                        json.dumps(diff),
                        reason,
                        lineage_node_id,
                        correlation_id,
                        ip_address,
                        user_agent,
                    )
                )
                conn.commit()

        self.logger.info(f"Logged DELETE: {table}/{entity_id} by {user}")
        return audit_id

    def get_events(
        self, entity_type: str, entity_id: str, limit: int = 1000
    ) -> list[AuditEvent]:
        """Get all audit events for a specific entity.

        Args:
            entity_type: Table name
            entity_id: Business key
            limit: Maximum results

        Returns:
            List of AuditEvents (most recent first)
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT audit_id, timestamp, user_name, action, entity_type, entity_id,
                              change_type, old_values, new_values, diff, reason,
                              lineage_node_id, correlation_id, ip_address, user_agent, created_at
                       FROM public.audit_trail
                       WHERE entity_type = %s AND entity_id = %s
                       ORDER BY timestamp DESC
                       LIMIT %s""",
                    (entity_type, entity_id, limit)
                )
                rows = cur.fetchall()

                events = []
                for row in rows:
                    events.append(
                        AuditEvent(
                            audit_id=row[0],
                            timestamp=row[1],
                            user_name=row[2],
                            action=row[3],
                            entity_type=row[4],
                            entity_id=row[5],
                            change_type=row[6],
                            old_values=json.loads(row[7]) if row[7] else None,
                            new_values=json.loads(row[8]) if row[8] else None,
                            diff=json.loads(row[9]) if row[9] else None,
                            reason=row[10],
                            lineage_node_id=row[11],
                            correlation_id=row[12],
                            ip_address=row[13],
                            user_agent=row[14],
                            created_at=row[15],
                        )
                    )
                return events

    def get_events_by_user(
        self, user: str, start_date: date, end_date: date, limit: int = 10000
    ) -> list[AuditEvent]:
        """Get all audit events by a specific user in a date range.

        Args:
            user: User name
            start_date: Range start (inclusive)
            end_date: Range end (inclusive)
            limit: Maximum results

        Returns:
            List of AuditEvents
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT audit_id, timestamp, user_name, action, entity_type, entity_id,
                              change_type, old_values, new_values, diff, reason,
                              lineage_node_id, correlation_id, ip_address, user_agent, created_at
                       FROM public.audit_trail
                       WHERE user_name = %s
                         AND DATE(timestamp) >= %s
                         AND DATE(timestamp) <= %s
                       ORDER BY timestamp DESC
                       LIMIT %s""",
                    (user, start_date, end_date, limit)
                )
                rows = cur.fetchall()

                events = []
                for row in rows:
                    events.append(
                        AuditEvent(
                            audit_id=row[0],
                            timestamp=row[1],
                            user_name=row[2],
                            action=row[3],
                            entity_type=row[4],
                            entity_id=row[5],
                            change_type=row[6],
                            old_values=json.loads(row[7]) if row[7] else None,
                            new_values=json.loads(row[8]) if row[8] else None,
                            diff=json.loads(row[9]) if row[9] else None,
                            reason=row[10],
                            lineage_node_id=row[11],
                            correlation_id=row[12],
                            ip_address=row[13],
                            user_agent=row[14],
                            created_at=row[15],
                        )
                    )
                return events

    def get_events_by_action(self, action: str, limit: int = 10000) -> list[AuditEvent]:
        """Get all audit events of a specific action type.

        Args:
            action: ActionType value (INSERT, UPDATE, DELETE, etc.)
            limit: Maximum results

        Returns:
            List of AuditEvents
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT audit_id, timestamp, user_name, action, entity_type, entity_id,
                              change_type, old_values, new_values, diff, reason,
                              lineage_node_id, correlation_id, ip_address, user_agent, created_at
                       FROM public.audit_trail
                       WHERE action = %s
                       ORDER BY timestamp DESC
                       LIMIT %s""",
                    (action, limit)
                )
                rows = cur.fetchall()

                events = []
                for row in rows:
                    events.append(
                        AuditEvent(
                            audit_id=row[0],
                            timestamp=row[1],
                            user_name=row[2],
                            action=row[3],
                            entity_type=row[4],
                            entity_id=row[5],
                            change_type=row[6],
                            old_values=json.loads(row[7]) if row[7] else None,
                            new_values=json.loads(row[8]) if row[8] else None,
                            diff=json.loads(row[9]) if row[9] else None,
                            reason=row[10],
                            lineage_node_id=row[11],
                            correlation_id=row[12],
                            ip_address=row[13],
                            user_agent=row[14],
                            created_at=row[15],
                        )
                    )
                return events

    def search_events(self, criteria: dict[str, Any], limit: int = 10000) -> list[AuditEvent]:
        """Search audit events by multiple criteria.

        Supported criteria keys:
            - entity_type: str
            - entity_id: str
            - user_name: str
            - action: str
            - change_type: str
            - start_date: date or datetime
            - end_date: date or datetime
            - reason_contains: str (substring match)

        Args:
            criteria: Search filters
            limit: Maximum results

        Returns:
            List of matching AuditEvents
        """
        query = "SELECT audit_id, timestamp, user_name, action, entity_type, entity_id, change_type, old_values, new_values, diff, reason, lineage_node_id, correlation_id, ip_address, user_agent, created_at FROM public.audit_trail WHERE 1=1"
        params = []

        if "entity_type" in criteria:
            query += " AND entity_type = %s"
            params.append(criteria["entity_type"])

        if "entity_id" in criteria:
            query += " AND entity_id = %s"
            params.append(criteria["entity_id"])

        if "user_name" in criteria:
            query += " AND user_name = %s"
            params.append(criteria["user_name"])

        if "action" in criteria:
            query += " AND action = %s"
            params.append(criteria["action"])

        if "change_type" in criteria:
            query += " AND change_type = %s"
            params.append(criteria["change_type"])

        if "start_date" in criteria:
            query += " AND timestamp >= %s"
            params.append(criteria["start_date"])

        if "end_date" in criteria:
            query += " AND timestamp <= %s"
            params.append(criteria["end_date"])

        if "reason_contains" in criteria:
            query += " AND reason ILIKE %s"
            params.append(f"%{criteria['reason_contains']}%")

        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

                events = []
                for row in rows:
                    events.append(
                        AuditEvent(
                            audit_id=row[0],
                            timestamp=row[1],
                            user_name=row[2],
                            action=row[3],
                            entity_type=row[4],
                            entity_id=row[5],
                            change_type=row[6],
                            old_values=json.loads(row[7]) if row[7] else None,
                            new_values=json.loads(row[8]) if row[8] else None,
                            diff=json.loads(row[9]) if row[9] else None,
                            reason=row[10],
                            lineage_node_id=row[11],
                            correlation_id=row[12],
                            ip_address=row[13],
                            user_agent=row[14],
                            created_at=row[15],
                        )
                    )
                return events

    def export_csv(self, output: IO, criteria: dict[str, Any] | None = None) -> int:
        """Export audit events to CSV.

        Args:
            output: File object to write to
            criteria: Optional search criteria

        Returns:
            Number of rows exported
        """
        if criteria:
            events = self.search_events(criteria, limit=999999)
        else:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT audit_id, timestamp, user_name, action, entity_type, entity_id,
                                  change_type, reason
                           FROM public.audit_trail
                           ORDER BY timestamp DESC"""
                    )
                    rows = cur.fetchall()
                    events = [
                        AuditEvent(
                            audit_id=row[0],
                            timestamp=row[1],
                            user_name=row[2],
                            action=row[3],
                            entity_type=row[4],
                            entity_id=row[5],
                            change_type=row[6],
                            reason=row[7],
                        )
                        for row in rows
                    ]

        writer = csv.DictWriter(
            output,
            fieldnames=[
                "audit_id",
                "timestamp",
                "user_name",
                "action",
                "entity_type",
                "entity_id",
                "change_type",
                "reason",
            ],
        )
        writer.writeheader()
        for event in events:
            writer.writerow(
                {
                    "audit_id": event.audit_id,
                    "timestamp": event.timestamp.isoformat(),
                    "user_name": event.user_name,
                    "action": event.action,
                    "entity_type": event.entity_type,
                    "entity_id": event.entity_id,
                    "change_type": event.change_type,
                    "reason": event.reason or "",
                }
            )

        return len(events)

    def export_json(self, criteria: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Export audit events to JSON-serializable list.

        Args:
            criteria: Optional search criteria

        Returns:
            List of event dicts
        """
        if criteria:
            events = self.search_events(criteria, limit=999999)
        else:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT audit_id, timestamp, user_name, action, entity_type, entity_id,
                                  change_type, old_values, new_values, diff, reason,
                                  lineage_node_id, correlation_id, ip_address, user_agent, created_at
                           FROM public.audit_trail
                           ORDER BY timestamp DESC"""
                    )
                    rows = cur.fetchall()
                    events = [
                        AuditEvent(
                            audit_id=row[0],
                            timestamp=row[1],
                            user_name=row[2],
                            action=row[3],
                            entity_type=row[4],
                            entity_id=row[5],
                            change_type=row[6],
                            old_values=json.loads(row[7]) if row[7] else None,
                            new_values=json.loads(row[8]) if row[8] else None,
                            diff=json.loads(row[9]) if row[9] else None,
                            reason=row[10],
                            lineage_node_id=row[11],
                            correlation_id=row[12],
                            ip_address=row[13],
                            user_agent=row[14],
                            created_at=row[15],
                        )
                        for row in rows
                    ]

        return [event.to_dict() for event in events]

    def generate_compliance_report(self) -> dict[str, Any]:
        """Generate compliance report from audit trail.

        Returns:
            Dict with:
                - total_events: Total audit entries
                - date_range: First to last event
                - actions: Count by action type
                - users: List of all users
                - entities: Count of unique entities modified
                - coverage: Percentage of time period covered
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Total events
                cur.execute("SELECT COUNT(*) FROM public.audit_trail")
                total = cur.fetchone()[0]

                # Date range
                cur.execute(
                    """SELECT MIN(timestamp), MAX(timestamp)
                       FROM public.audit_trail"""
                )
                min_ts, max_ts = cur.fetchone()

                # Actions by type
                cur.execute(
                    """SELECT action, COUNT(*)
                       FROM public.audit_trail
                       GROUP BY action"""
                )
                actions = {row[0]: row[1] for row in cur.fetchall()}

                # Users
                cur.execute(
                    """SELECT DISTINCT user_name
                       FROM public.audit_trail
                       ORDER BY user_name"""
                )
                users = [row[0] for row in cur.fetchall()]

                # Unique entities
                cur.execute(
                    """SELECT COUNT(DISTINCT entity_id)
                       FROM public.audit_trail"""
                )
                unique_entities = cur.fetchone()[0]

                # Unique entity types
                cur.execute(
                    """SELECT COUNT(DISTINCT entity_type)
                       FROM public.audit_trail"""
                )
                unique_types = cur.fetchone()[0]

        duration_days = (max_ts - min_ts).days if min_ts and max_ts else 0

        return {
            "total_events": total,
            "date_range": {
                "start": min_ts.isoformat() if min_ts else None,
                "end": max_ts.isoformat() if max_ts else None,
                "duration_days": duration_days,
            },
            "actions": actions,
            "users": users,
            "user_count": len(users),
            "unique_entities": unique_entities,
            "unique_entity_types": unique_types,
            "events_per_day": total / max(duration_days, 1),
        }
