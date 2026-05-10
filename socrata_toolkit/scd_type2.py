"""Slowly Changing Dimension Type 2 (SCD Type 2) implementation.

This module provides comprehensive SCD Type 2 support for maintaining historical
versions of records with effective dates. SCD Type 2 keeps all versions of a record
by adding start_date, end_date, and is_current columns, allowing temporal queries
and historical analysis.

Key Features:
    - Automatic version management with effective dates
    - Immutable historical records
    - Temporal queries (as-of date)
    - Hash-based change detection
    - Integration with PostgreSQL persistence

Classes:
    SCDRecord: Represents a single version of a record
    SCDType2Manager: Manages SCD Type 2 operations for tables

Example:
    >>> manager = SCDType2Manager(dsn="postgresql://...", table="sidewalk_conditions_scd")
    >>> record_id = manager.manage_record(
    ...     business_key="sidewalk_123",
    ...     new_data={"condition": "excellent", "material": "concrete"}
    ... )
    >>> current = manager.get_current_record("sidewalk_123")
    >>> history = manager.get_record_history("sidewalk_123")
    >>> as_of = manager.get_as_of("sidewalk_123", datetime(2026, 3, 15))
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, asdict, field
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


class DMLType(Enum):
    """Type of data modification operation."""
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass
class SCDRecord:
    """Represents a single version of a SCD Type 2 record.
    
    This class encapsulates all the metadata needed to track a single version
    of a record over time. Multiple SCDRecords with the same business_key
    represent the evolution of that entity.
    
    Attributes:
        scd_id: Unique identifier for this SCD record version
        business_key: Immutable identifier across all versions
        start_date: When this version became effective
        end_date: When this version ended (None = current version)
        is_current: True if this is the current version
        scd_hash: MD5 hash of data_fields for change detection
        data_fields: Dict of all mutable columns
        metadata: Dict containing source_system, dml_type, row_version, etc.
        created_at: When this record was created in the system
    """
    scd_id: str
    business_key: str
    start_date: datetime
    end_date: Optional[datetime]
    is_current: bool
    scd_hash: str
    data_fields: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SCDRecord:
        """Create an SCDRecord from a dictionary."""
        return cls(
            scd_id=data.get("scd_id", str(uuid.uuid4())),
            business_key=data["business_key"],
            start_date=data["start_date"],
            end_date=data.get("end_date"),
            is_current=data.get("is_current", True),
            scd_hash=data.get("scd_hash", ""),
            data_fields=data.get("data_fields", {}),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now(timezone.utc)),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "scd_id": self.scd_id,
            "business_key": self.business_key,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_current": self.is_current,
            "scd_hash": self.scd_hash,
            "data_fields": self.data_fields,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class SCDType2Manager:
    """Manages SCD Type 2 operations for a table.
    
    This class handles all SCD Type 2 operations: version tracking, historical
    records, temporal queries, and change detection. It uses MD5 hashing to
    detect actual data changes (avoiding unnecessary new versions).
    
    The manager operates on PostgreSQL and maintains immutable history
    with effective dates.
    """

    def __init__(self, dsn: str, table: str) -> None:
        """Initialize SCD Type 2 manager.
        
        Args:
            dsn: PostgreSQL connection string
            table: Table name containing SCD records
            
        Raises:
            ImportError: If psycopg is not installed
        """
        if psycopg is None:
            raise ImportError("Install postgres extras: pip install '.[postgres]'")
        self.dsn = dsn
        self.table = table
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
    def _calculate_hash(data: Dict[str, Any]) -> str:
        """Calculate MD5 hash of data fields.
        
        Args:
            data: Dictionary of data fields
            
        Returns:
            32-character hex MD5 hash
        """
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(json_str.encode()).hexdigest()

    def manage_record(
        self,
        business_key: str,
        new_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Manage a SCD record: insert, update, or do nothing.
        
        This is the primary method for managing SCD Type 2 records. It:
        1. Checks if business_key exists
        2. If new: creates INSERT record with start_date = now()
        3. If exists and unchanged: returns existing id
        4. If exists and changed: closes old version, creates new version
        
        Args:
            business_key: Unique identifier for entity across time
            new_data: Current data values for the record
            metadata: Optional metadata (source_system, etc.)
            
        Returns:
            scd_id of the (possibly new) current record
        """
        new_hash = self._calculate_hash(new_data)
        now = datetime.now(timezone.utc)
        
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Check for existing current record
                cur.execute(
                    f"""SELECT scd_id, scd_hash, data_values 
                       FROM {sql.Identifier(self.table)}
                       WHERE business_key = %s AND is_current = TRUE
                       LIMIT 1""",
                    (business_key,)
                )
                current = cur.fetchone()
                
                if current is None:
                    # New record: INSERT
                    scd_id = str(uuid.uuid4())
                    meta = metadata or {}
                    meta["dml_type"] = DMLType.INSERT.value
                    meta["row_version"] = 1
                    
                    cur.execute(
                        f"""INSERT INTO {sql.Identifier(self.table)}
                           (scd_id, business_key, start_date, end_date, is_current,
                            scd_hash, data_values, metadata)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            scd_id,
                            business_key,
                            now,
                            None,
                            True,
                            new_hash,
                            json.dumps(new_data),
                            json.dumps(meta),
                        )
                    )
                    conn.commit()
                    self.logger.debug(f"Created new SCD record: {scd_id} for {business_key}")
                    return scd_id
                
                current_scd_id, current_hash, current_data = current
                
                # Check if data changed
                if current_hash == new_hash:
                    # No change: return existing
                    self.logger.debug(f"No change detected for {business_key}")
                    return current_scd_id
                
                # Data changed: close old version, insert new
                # Close old version
                cur.execute(
                    f"""UPDATE {sql.Identifier(self.table)}
                       SET end_date = %s, is_current = FALSE
                       WHERE scd_id = %s""",
                    (now, current_scd_id)
                )
                
                # Insert new version
                scd_id = str(uuid.uuid4())
                meta = metadata or {}
                meta["dml_type"] = DMLType.UPDATE.value
                current_meta = json.loads(current_data.get("metadata", "{}")) if isinstance(current_data, dict) else {}
                meta["row_version"] = current_meta.get("row_version", 0) + 1
                
                cur.execute(
                    f"""INSERT INTO {sql.Identifier(self.table)}
                       (scd_id, business_key, start_date, end_date, is_current,
                        scd_hash, data_values, metadata)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        scd_id,
                        business_key,
                        now,
                        None,
                        True,
                        new_hash,
                        json.dumps(new_data),
                        json.dumps(meta),
                    )
                )
                conn.commit()
                self.logger.debug(f"Updated SCD record: {current_scd_id} -> {scd_id} for {business_key}")
                return scd_id

    def get_current_record(self, business_key: str) -> Optional[SCDRecord]:
        """Get the current (is_current=TRUE) version of a record.
        
        Args:
            business_key: Unique identifier
            
        Returns:
            SCDRecord or None if not found
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT scd_id, business_key, start_date, end_date, is_current,
                              scd_hash, data_values, metadata, created_at
                       FROM {sql.Identifier(self.table)}
                       WHERE business_key = %s AND is_current = TRUE
                       LIMIT 1""",
                    (business_key,)
                )
                row = cur.fetchone()
                
                if row is None:
                    return None
                
                return SCDRecord(
                    scd_id=row[0],
                    business_key=row[1],
                    start_date=row[2],
                    end_date=row[3],
                    is_current=row[4],
                    scd_hash=row[5],
                    data_fields=json.loads(row[6]) if isinstance(row[6], str) else row[6],
                    metadata=json.loads(row[7]) if isinstance(row[7], str) else row[7],
                    created_at=row[8],
                )

    def get_record_history(self, business_key: str) -> List[SCDRecord]:
        """Get all versions of a record ordered by start_date DESC.
        
        Args:
            business_key: Unique identifier
            
        Returns:
            List of SCDRecords (most recent first)
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT scd_id, business_key, start_date, end_date, is_current,
                              scd_hash, data_values, metadata, created_at
                       FROM {sql.Identifier(self.table)}
                       WHERE business_key = %s
                       ORDER BY start_date DESC""",
                    (business_key,)
                )
                rows = cur.fetchall()
                
                records = []
                for row in rows:
                    records.append(
                        SCDRecord(
                            scd_id=row[0],
                            business_key=row[1],
                            start_date=row[2],
                            end_date=row[3],
                            is_current=row[4],
                            scd_hash=row[5],
                            data_fields=json.loads(row[6]) if isinstance(row[6], str) else row[6],
                            metadata=json.loads(row[7]) if isinstance(row[7], str) else row[7],
                            created_at=row[8],
                        )
                    )
                return records

    def get_as_of(
        self, business_key: str, as_of_date: datetime
    ) -> Optional[SCDRecord]:
        """Get the record version effective as of a specific date.
        
        This enables temporal queries like "show me the data as of March 15, 2024".
        Returns the version where start_date <= as_of_date < end_date.
        
        Args:
            business_key: Unique identifier
            as_of_date: Point in time to query
            
        Returns:
            SCDRecord effective at that date, or None
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT scd_id, business_key, start_date, end_date, is_current,
                              scd_hash, data_values, metadata, created_at
                       FROM {sql.Identifier(self.table)}
                       WHERE business_key = %s
                         AND start_date <= %s
                         AND (end_date IS NULL OR end_date > %s)
                       LIMIT 1""",
                    (business_key, as_of_date, as_of_date)
                )
                row = cur.fetchone()
                
                if row is None:
                    return None
                
                return SCDRecord(
                    scd_id=row[0],
                    business_key=row[1],
                    start_date=row[2],
                    end_date=row[3],
                    is_current=row[4],
                    scd_hash=row[5],
                    data_fields=json.loads(row[6]) if isinstance(row[6], str) else row[6],
                    metadata=json.loads(row[7]) if isinstance(row[7], str) else row[7],
                    created_at=row[8],
                )

    def mark_deleted(
        self,
        business_key: str,
        reason: str = "Manual deletion",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Mark a record as deleted (soft delete via SCD).
        
        Creates a new version with is_current=TRUE but with all data fields set to null,
        signifying a logical delete. Previous versions remain intact for audit.
        
        Args:
            business_key: Unique identifier
            reason: Reason for deletion
            metadata: Optional metadata
            
        Returns:
            True if successful, False if record not found
        """
        current = self.get_current_record(business_key)
        if current is None:
            return False
        
        # Create empty version
        meta = metadata or {}
        meta["dml_type"] = DMLType.DELETE.value
        meta["deletion_reason"] = reason
        
        self.manage_record(
            business_key=business_key,
            new_data={},
            metadata=meta,
        )
        return True

    def restore_deleted(self, business_key: str) -> bool:
        """Restore a soft-deleted record to its previous non-deleted state.
        
        Args:
            business_key: Unique identifier
            
        Returns:
            True if successful, False if no previous version found
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Find the last non-empty version before deletion
                cur.execute(
                    f"""SELECT scd_id, data_values FROM {sql.Identifier(self.table)}
                       WHERE business_key = %s
                         AND (data_values IS NOT NULL AND data_values != '{{}}')
                       ORDER BY start_date DESC
                       LIMIT 1""",
                    (business_key,)
                )
                row = cur.fetchone()
                
                if row is None:
                    return False
                
                prev_id, prev_data = row
                prev_dict = json.loads(prev_data) if isinstance(prev_data, str) else prev_data
                
                meta = {
                    "dml_type": "RESTORE",
                    "restored_from": prev_id,
                }
                
                self.manage_record(
                    business_key=business_key,
                    new_data=prev_dict,
                    metadata=meta,
                )
                return True

    def validate_scd(self) -> Dict[str, Any]:
        """Validate SCD Type 2 integrity constraints.
        
        Checks:
        1. No overlapping date ranges for same business_key
        2. At most one is_current=TRUE per business_key
        3. All records have non-null start_date
        4. end_date >= start_date where both exist
        5. Hash consistency
        
        Returns:
            Dict with validation results: {
                "valid": bool,
                "issues": List[str],
                "stats": Dict
            }
        """
        issues = []
        stats = {}
        
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Check for overlapping dates
                cur.execute(
                    f"""SELECT business_key, COUNT(*) as cnt
                       FROM {sql.Identifier(self.table)}
                       WHERE is_current = TRUE
                       GROUP BY business_key
                       HAVING COUNT(*) > 1"""
                )
                if cur.fetchall():
                    issues.append("Multiple is_current=TRUE records found for same business_key")
                
                # Check for invalid date ranges
                cur.execute(
                    f"""SELECT COUNT(*) as cnt
                       FROM {sql.Identifier(self.table)}
                       WHERE end_date IS NOT NULL AND end_date < start_date"""
                )
                invalid_ranges = cur.fetchone()[0]
                if invalid_ranges > 0:
                    issues.append(f"{invalid_ranges} records with end_date < start_date")
                
                # Count stats
                cur.execute(
                    f"""SELECT 
                         COUNT(*) as total,
                         COUNT(DISTINCT business_key) as unique_keys,
                         SUM(CASE WHEN is_current THEN 1 ELSE 0 END) as current_count,
                         SUM(CASE WHEN is_current THEN 0 ELSE 1 END) as historical_count
                       FROM {sql.Identifier(self.table)}"""
                )
                row = cur.fetchone()
                stats = {
                    "total_records": row[0],
                    "unique_keys": row[1],
                    "current_records": row[2],
                    "historical_records": row[3],
                }
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "stats": stats,
        }

    def get_change_count(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, int]:
        """Count SCD changes in a date range.
        
        Args:
            start_date: Range start (inclusive)
            end_date: Range end (inclusive)
            
        Returns:
            Dict with counts by DML type
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT metadata->>'dml_type' as dml_type, COUNT(*) as cnt
                       FROM {sql.Identifier(self.table)}
                       WHERE start_date >= %s AND start_date <= %s
                       GROUP BY metadata->>'dml_type'""",
                    (start_date, end_date)
                )
                rows = cur.fetchall()
                return {row[0] or "UNKNOWN": row[1] for row in rows}

    def export_current(self) -> List[Dict[str, Any]]:
        """Export all current (is_current=TRUE) records.
        
        Returns:
            List of current records as dicts
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT scd_id, business_key, start_date, end_date, is_current,
                              scd_hash, data_values, metadata
                       FROM {sql.Identifier(self.table)}
                       WHERE is_current = TRUE
                       ORDER BY business_key"""
                )
                rows = cur.fetchall()
                
                result = []
                for row in rows:
                    result.append({
                        "scd_id": row[0],
                        "business_key": row[1],
                        "start_date": row[2].isoformat(),
                        "end_date": row[3].isoformat() if row[3] else None,
                        "is_current": row[4],
                        "scd_hash": row[5],
                        "data_values": json.loads(row[6]) if isinstance(row[6], str) else row[6],
                        "metadata": json.loads(row[7]) if isinstance(row[7], str) else row[7],
                    })
                return result
