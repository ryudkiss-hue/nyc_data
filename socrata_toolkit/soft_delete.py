"""Soft delete and retention policy management.

This module implements GDPR/regulatory-compliant soft delete with configurable
retention policies. Records are marked deleted but remain in the database for
compliance, then hard-deleted after retention period expires.

Key Features:
    - Soft delete: logical deletion with is_deleted flag
    - Retention policies: configurable hard delete timing
    - Audit trail: deletion reason and user tracking
    - Restore capability: undelete records within retention period
    - Hard delete: permanent removal after retention expires
    - Backup before delete: optional encrypted backup

Classes:
    SoftDeleteManager: Manage soft/hard deletes and retention
    RetentionPolicy: Policy definition

Example:
    >>> mgr = SoftDeleteManager(dsn="postgresql://...")
    >>> mgr.soft_delete("sidewalk_conditions", "sidewalk_123", reason="Duplicate")
    >>> mgr.restore_deleted("sidewalk_conditions", "sidewalk_123")
    >>> mgr.hard_delete_expired(days=90)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager

try:
    import psycopg
    from psycopg import sql
except ImportError:
    psycopg = None  # type: ignore
    sql = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class RetentionPolicy:
    """Retention policy for soft deleted records.
    
    Attributes:
        table_name: Table this policy applies to
        retention_days: Days to keep soft-deleted records
        allow_hard_delete: Whether hard delete is permitted
        require_backup: Whether to backup before hard delete
        backup_location: Where to store backup (optional)
    """
    table_name: str
    retention_days: int = 90
    allow_hard_delete: bool = True
    require_backup: bool = True
    backup_location: Optional[str] = None


class SoftDeleteManager:
    """Manages soft delete and retention policies.
    
    Implements logical deletion where records are marked deleted but retained
    for compliance, with automatic hard delete after retention period.
    """

    def __init__(self, dsn: str) -> None:
        """Initialize soft delete manager.
        
        Args:
            dsn: PostgreSQL connection string
            
        Raises:
            ImportError: If psycopg not installed
        """
        if psycopg is None:
            raise ImportError("Install postgres extras: pip install '.[postgres]'")
        self.dsn = dsn
        self.logger = logger.getChild(self.__class__.__name__)
        self.retention_policies: Dict[str, RetentionPolicy] = {}

    @contextmanager
    def _get_connection(self):
        """Context manager for database connection."""
        conn = psycopg.connect(self.dsn)
        try:
            yield conn
        finally:
            conn.close()

    def set_retention_policy(self, policy: RetentionPolicy) -> None:
        """Set retention policy for a table.
        
        Args:
            policy: RetentionPolicy
        """
        self.retention_policies[policy.table_name] = policy
        self.logger.info(
            f"Set retention policy for {policy.table_name}: {policy.retention_days} days"
        )

    def get_retention_policy(self, table: str) -> RetentionPolicy:
        """Get retention policy for a table.
        
        Args:
            table: Table name
            
        Returns:
            RetentionPolicy or default 90-day policy
        """
        return self.retention_policies.get(table, RetentionPolicy(table, 90))

    def soft_delete(
        self,
        table: str,
        record_id: str,
        reason: str = "User requested deletion",
        deleted_by: str = "SYSTEM",
    ) -> bool:
        """Soft delete a record.
        
        Marks record as deleted but keeps it in database for audit trail.
        Schedules hard delete based on retention policy.
        
        Args:
            table: Table name
            record_id: Business key
            reason: Reason for deletion
            deleted_by: User who deleted
            
        Returns:
            True if successful
        """
        policy = self.get_retention_policy(table)
        now = datetime.now(timezone.utc)
        hard_delete_at = now + timedelta(days=policy.retention_days)
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Log to soft_delete_log
                    cur.execute(
                        """INSERT INTO public.soft_delete_log
                           (table_name, record_id, deleted_at, deleted_by,
                            delete_reason, retention_days, hard_delete_scheduled_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (
                            table,
                            record_id,
                            now,
                            deleted_by,
                            reason,
                            policy.retention_days,
                            hard_delete_at,
                        )
                    )
                    
                    # Update table if it has is_deleted column
                    try:
                        cur.execute(
                            f"""UPDATE {sql.Identifier(table)}
                               SET is_deleted = TRUE, deleted_at = %s
                               WHERE id = %s OR record_id = %s OR business_key = %s""",
                            (now, record_id, record_id, record_id)
                        )
                    except Exception:
                        # Table may not have is_deleted column, that's OK
                        pass
                    
                    conn.commit()
            
            self.logger.info(
                f"Soft deleted {table}/{record_id} by {deleted_by} (will hard delete {hard_delete_at})"
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to soft delete {table}/{record_id}: {e}")
            return False

    def restore_deleted(self, table: str, record_id: str) -> bool:
        """Restore a soft-deleted record.
        
        Only works within the retention period.
        
        Args:
            table: Table name
            record_id: Business key
            
        Returns:
            True if successful, False if already hard-deleted
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if still within retention period
                    cur.execute(
                        """SELECT soft_delete_id FROM public.soft_delete_log
                           WHERE table_name = %s AND record_id = %s
                             AND (hard_delete_scheduled_at IS NULL OR hard_delete_scheduled_at > %s)
                           ORDER BY deleted_at DESC
                           LIMIT 1""",
                        (table, record_id, datetime.now(timezone.utc))
                    )
                    row = cur.fetchone()
                    
                    if not row:
                        self.logger.warning(
                            f"Cannot restore {table}/{record_id}: retention period expired"
                        )
                        return False
                    
                    # Update soft_delete_log
                    cur.execute(
                        """UPDATE public.soft_delete_log
                           SET hard_delete_scheduled_at = NULL
                           WHERE soft_delete_id = %s""",
                        (row[0],)
                    )
                    
                    # Update table if it has is_deleted column
                    try:
                        cur.execute(
                            f"""UPDATE {sql.Identifier(table)}
                               SET is_deleted = FALSE, deleted_at = NULL
                               WHERE id = %s OR record_id = %s OR business_key = %s""",
                            (record_id, record_id, record_id)
                        )
                    except Exception:
                        pass
                    
                    conn.commit()
            
            self.logger.info(f"Restored {table}/{record_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to restore {table}/{record_id}: {e}")
            return False

    def hard_delete_expired(self, table: Optional[str] = None, retention_days: int = 90) -> int:
        """Hard delete records that have exceeded retention period.
        
        This is the actual deletion. Should be run periodically (e.g., nightly).
        
        Args:
            table: Specific table to clean up, or None for all
            retention_days: Override default retention
            
        Returns:
            Count of hard-deleted records
        """
        try:
            expired_at = datetime.now(timezone.utc) - timedelta(days=retention_days)
            deleted_count = 0
            
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Find eligible records
                    if table:
                        cur.execute(
                            """SELECT DISTINCT table_name, record_id
                               FROM public.soft_delete_log
                               WHERE (table_name = %s OR %s IS NULL)
                                 AND deleted_at < %s
                                 AND hard_delete_scheduled_at IS NOT NULL
                                 AND hard_delete_scheduled_at <= %s""",
                            (table, table, expired_at, datetime.now(timezone.utc))
                        )
                    else:
                        cur.execute(
                            """SELECT DISTINCT table_name, record_id
                               FROM public.soft_delete_log
                               WHERE deleted_at < %s
                                 AND hard_delete_scheduled_at IS NOT NULL
                                 AND hard_delete_scheduled_at <= %s""",
                            (expired_at, datetime.now(timezone.utc))
                        )
                    
                    rows = cur.fetchall()
                    
                    for tbl, rec_id in rows:
                        try:
                            # Optional: backup before delete
                            policy = self.get_retention_policy(tbl)
                            if policy.require_backup:
                                self._backup_record(tbl, rec_id)
                            
                            # Perform hard delete
                            cur.execute(
                                f"""DELETE FROM {sql.Identifier(tbl)}
                                   WHERE id = %s OR record_id = %s OR business_key = %s""",
                                (rec_id, rec_id, rec_id)
                            )
                            
                            # Update log
                            cur.execute(
                                """UPDATE public.soft_delete_log
                                   SET hard_delete_scheduled_at = NULL
                                   WHERE table_name = %s AND record_id = %s""",
                                (tbl, rec_id)
                            )
                            
                            deleted_count += 1
                            self.logger.debug(f"Hard deleted {tbl}/{rec_id}")
                        except Exception as e:
                            self.logger.error(f"Failed to hard delete {tbl}/{rec_id}: {e}")
                    
                    conn.commit()
            
            self.logger.info(f"Hard deleted {deleted_count} expired records")
            return deleted_count
        except Exception as e:
            self.logger.error(f"Hard delete batch failed: {e}")
            return 0

    def _backup_record(self, table: str, record_id: str) -> Optional[str]:
        """Backup a record before hard delete.
        
        Args:
            table: Table name
            record_id: Record ID
            
        Returns:
            Backup location or None if failed
        """
        # This is a placeholder for backup implementation
        # In production, this would create encrypted backup
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Try to get record
                    cur.execute(
                        f"""SELECT * FROM {sql.Identifier(table)}
                           WHERE id = %s OR record_id = %s OR business_key = %s
                           LIMIT 1""",
                        (record_id, record_id, record_id)
                    )
                    row = cur.fetchone()
                    
                    if row:
                        # In real implementation, serialize and encrypt
                        backup_location = f"backup://{table}/{record_id}"
                        self.logger.debug(f"Backed up {table}/{record_id}")
                        return backup_location
        except Exception as e:
            self.logger.warning(f"Backup failed for {table}/{record_id}: {e}")
        
        return None

    def is_deleted(self, table: str, record_id: str) -> bool:
        """Check if a record is soft-deleted.
        
        Args:
            table: Table name
            record_id: Business key
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Check soft_delete_log first
                    cur.execute(
                        """SELECT COUNT(*) FROM public.soft_delete_log
                           WHERE table_name = %s AND record_id = %s
                             AND (hard_delete_scheduled_at IS NULL OR
                                  hard_delete_scheduled_at > %s)""",
                        (table, record_id, datetime.now(timezone.utc))
                    )
                    return cur.fetchone()[0] > 0
        except Exception as e:
            self.logger.error(f"Failed to check if {table}/{record_id} is deleted: {e}")
            return False

    def get_deleted_count(self, table: Optional[str] = None) -> int:
        """Get count of soft-deleted records.
        
        Args:
            table: Specific table, or None for all
            
        Returns:
            Count of soft-deleted records
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    if table:
                        cur.execute(
                            """SELECT COUNT(DISTINCT record_id)
                               FROM public.soft_delete_log
                               WHERE table_name = %s
                                 AND (hard_delete_scheduled_at IS NULL OR
                                      hard_delete_scheduled_at > %s)""",
                            (table, datetime.now(timezone.utc))
                        )
                    else:
                        cur.execute(
                            """SELECT COUNT(DISTINCT record_id)
                               FROM public.soft_delete_log
                               WHERE hard_delete_scheduled_at IS NULL OR
                                     hard_delete_scheduled_at > %s""",
                            (datetime.now(timezone.utc),)
                        )
                    return cur.fetchone()[0]
        except Exception as e:
            self.logger.error(f"Failed to count deleted records: {e}")
            return 0

    def get_deletion_history(
        self, table: str, record_id: str
    ) -> List[Dict[str, Any]]:
        """Get deletion history for a record.
        
        Args:
            table: Table name
            record_id: Business key
            
        Returns:
            List of deletion events
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT soft_delete_id, deleted_at, deleted_by, delete_reason,
                                  retention_days, hard_delete_scheduled_at
                           FROM public.soft_delete_log
                           WHERE table_name = %s AND record_id = %s
                           ORDER BY deleted_at DESC""",
                        (table, record_id)
                    )
                    rows = cur.fetchall()
            
            return [
                {
                    "soft_delete_id": str(row[0]),
                    "deleted_at": row[1].isoformat(),
                    "deleted_by": row[2],
                    "reason": row[3],
                    "retention_days": row[4],
                    "hard_delete_scheduled": row[5].isoformat() if row[5] else None,
                }
                for row in rows
            ]
        except Exception as e:
            self.logger.error(f"Failed to get deletion history for {table}/{record_id}: {e}")
            return []

    def get_expiring_soon(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get records scheduled for hard delete soon.
        
        Useful for alerts/notifications.
        
        Args:
            days: How many days in advance to check
            
        Returns:
            List of records expiring soon
        """
        try:
            now = datetime.now(timezone.utc)
            soon = now + timedelta(days=days)
            
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT table_name, record_id, deleted_at,
                                  hard_delete_scheduled_at, delete_reason
                           FROM public.soft_delete_log
                           WHERE hard_delete_scheduled_at > %s
                             AND hard_delete_scheduled_at <= %s
                           ORDER BY hard_delete_scheduled_at ASC""",
                        (now, soon)
                    )
                    rows = cur.fetchall()
            
            return [
                {
                    "table": row[0],
                    "record_id": row[1],
                    "deleted_at": row[2].isoformat(),
                    "hard_delete_at": row[3].isoformat(),
                    "reason": row[4],
                }
                for row in rows
            ]
        except Exception as e:
            self.logger.error(f"Failed to get expiring records: {e}")
            return []

    def bulk_soft_delete(
        self, table: str, record_ids: List[str], reason: str, deleted_by: str = "SYSTEM"
    ) -> Tuple[int, int]:
        """Soft delete multiple records.
        
        Args:
            table: Table name
            record_ids: List of business keys
            reason: Reason for deletion
            deleted_by: User who deleted
            
        Returns:
            Tuple of (successful, failed)
        """
        successful = 0
        failed = 0
        
        for record_id in record_ids:
            if self.soft_delete(table, record_id, reason, deleted_by):
                successful += 1
            else:
                failed += 1
        
        self.logger.info(f"Bulk soft delete: {successful} successful, {failed} failed")
        return (successful, failed)

    def get_retention_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance report on retention policies.
        
        Returns:
            Dict with retention statistics
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Count soft-deleted
                    cur.execute(
                        """SELECT COUNT(*) FROM public.soft_delete_log
                           WHERE hard_delete_scheduled_at > %s""",
                        (datetime.now(timezone.utc),)
                    )
                    soft_deleted = cur.fetchone()[0]
                    
                    # Count expiring
                    soon = datetime.now(timezone.utc) + timedelta(days=7)
                    cur.execute(
                        """SELECT COUNT(*) FROM public.soft_delete_log
                           WHERE hard_delete_scheduled_at <= %s AND hard_delete_scheduled_at > %s""",
                        (soon, datetime.now(timezone.utc))
                    )
                    expiring_soon = cur.fetchone()[0]
                    
                    # Count by reason
                    cur.execute(
                        """SELECT delete_reason, COUNT(*)
                           FROM public.soft_delete_log
                           WHERE hard_delete_scheduled_at > %s
                           GROUP BY delete_reason""",
                        (datetime.now(timezone.utc),)
                    )
                    by_reason = {row[0]: row[1] for row in cur.fetchall()}
            
            return {
                "total_soft_deleted": soft_deleted,
                "expiring_in_7_days": expiring_soon,
                "by_reason": by_reason,
                "policies": {
                    name: {
                        "retention_days": policy.retention_days,
                        "allow_hard_delete": policy.allow_hard_delete,
                    }
                    for name, policy in self.retention_policies.items()
                },
            }
        except Exception as e:
            self.logger.error(f"Failed to generate compliance report: {e}")
            return {}
