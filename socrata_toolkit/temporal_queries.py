"""Temporal query support for SCD Type 2 records.

This module provides advanced temporal query capabilities for time-series analysis
of slowly changing dimensions. Enables "as-of" queries, version tracking, and
change pattern detection.

Key Features:
    - As-of date queries: show data as it was on a specific date
    - Version history: retrieve all versions with dates
    - Change detection: find what changed between dates
    - Time series: track metrics over time
    - Pattern analysis: detect change patterns

Classes:
    TemporalQuery: Main temporal query interface
    ChangeSummary: Summary of changes in a period
    ChangePattern: Pattern of changes to a record

Example:
    >>> tq = TemporalQuery(dsn="postgresql://...", table="sidewalk_conditions_scd")
    >>> record = tq.get_as_of("sidewalk_123", datetime(2026, 3, 15))
    >>> versions = tq.get_versions("sidewalk_123")
    >>> changes = tq.get_changes(date(2026, 3, 1), date(2026, 3, 31))
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, date, timezone
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
class ChangeSummary:
    """Summary of changes in a time period.
    
    Attributes:
        date: Date of changes
        business_key: Record identifier
        operation: Type of change (INSERT, UPDATE, DELETE)
        field_changes: Dict of field -> [old, new]
        changed_by: User who made change
        reason: Reason for change
    """
    date: date
    business_key: str
    operation: str
    field_changes: Dict[str, Tuple[Any, Any]]
    changed_by: str
    reason: Optional[str] = None


@dataclass
class ChangePattern:
    """Pattern of changes to a record.
    
    Attributes:
        business_key: Record identifier
        total_versions: Number of versions
        date_range: (start_date, end_date)
        fields_changed: Set of fields that changed
        change_frequency: Changes per day (approximate)
        most_recent_change: Datetime of last change
        change_types: Count of each operation type
    """
    business_key: str
    total_versions: int
    date_range: Tuple[datetime, datetime]
    fields_changed: set
    change_frequency: float
    most_recent_change: datetime
    change_types: Dict[str, int] = field(default_factory=dict)


class TemporalQuery:
    """Temporal query engine for SCD Type 2 tables.
    
    Provides time-series analysis, as-of queries, and change tracking
    for slowly changing dimensions.
    """

    def __init__(self, dsn: str, table: str) -> None:
        """Initialize temporal query engine.
        
        Args:
            dsn: PostgreSQL connection string
            table: SCD Type 2 table name
            
        Raises:
            ImportError: If psycopg not installed
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

    def get_as_of(self, business_key: str, as_of: datetime) -> Optional[Dict[str, Any]]:
        """Get record state as it existed on a specific date/time.
        
        This is the primary temporal query: returns the version of a record
        that was current at a specific point in time.
        
        Args:
            business_key: Record identifier
            as_of: Point in time to query
            
        Returns:
            Dict with record data or None if not found
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT scd_id, business_key, start_date, end_date, is_current,
                              scd_hash, data_values, metadata
                       FROM {sql.Identifier(self.table)}
                       WHERE business_key = %s
                         AND start_date <= %s
                         AND (end_date IS NULL OR end_date > %s)
                       LIMIT 1""",
                    (business_key, as_of, as_of)
                )
                row = cur.fetchone()
                
                if row is None:
                    return None
                
                return {
                    "scd_id": row[0],
                    "business_key": row[1],
                    "start_date": row[2].isoformat(),
                    "end_date": row[3].isoformat() if row[3] else None,
                    "is_current": row[4],
                    "scd_hash": row[5],
                    "data": json.loads(row[6]) if isinstance(row[6], str) else row[6],
                    "metadata": json.loads(row[7]) if isinstance(row[7], str) else row[7],
                }

    def get_versions(self, business_key: str) -> List[Dict[str, Any]]:
        """Get all versions of a record with dates.
        
        Args:
            business_key: Record identifier
            
        Returns:
            List of versions ordered by start_date DESC
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT scd_id, business_key, start_date, end_date, is_current,
                              scd_hash, data_values, metadata
                       FROM {sql.Identifier(self.table)}
                       WHERE business_key = %s
                       ORDER BY start_date DESC""",
                    (business_key,)
                )
                rows = cur.fetchall()
                
                versions = []
                for row in rows:
                    versions.append({
                        "scd_id": row[0],
                        "business_key": row[1],
                        "start_date": row[2].isoformat(),
                        "end_date": row[3].isoformat() if row[3] else None,
                        "is_current": row[4],
                        "scd_hash": row[5],
                        "data": json.loads(row[6]) if isinstance(row[6], str) else row[6],
                        "metadata": json.loads(row[7]) if isinstance(row[7], str) else row[7],
                    })
                return versions

    def get_changes(
        self, start_date: date, end_date: date, limit: int = 10000
    ) -> List[ChangeSummary]:
        """Get summary of all changes in a date range.
        
        Args:
            start_date: Range start (inclusive)
            end_date: Range end (inclusive)
            limit: Maximum results
            
        Returns:
            List of ChangeSummary objects
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT business_key, start_date, scd_hash, data_values, metadata
                       FROM {sql.Identifier(self.table)}
                       WHERE start_date::date >= %s
                         AND start_date::date <= %s
                       ORDER BY start_date DESC
                       LIMIT %s""",
                    (start_date, end_date, limit)
                )
                rows = cur.fetchall()
                
                changes = []
                for row in rows:
                    business_key = row[0]
                    change_date = row[1].date()
                    data = json.loads(row[3]) if isinstance(row[3], str) else row[3]
                    metadata = json.loads(row[4]) if isinstance(row[4], str) else row[4]
                    
                    # Determine operation from metadata
                    operation = metadata.get("dml_type", "UNKNOWN") if metadata else "UNKNOWN"
                    
                    changes.append(
                        ChangeSummary(
                            date=change_date,
                            business_key=business_key,
                            operation=operation,
                            field_changes={},  # Populated from diff if available
                            changed_by=metadata.get("changed_by", "UNKNOWN") if metadata else "UNKNOWN",
                            reason=metadata.get("reason"),
                        )
                    )
                
                return changes

    def track_metric_over_time(
        self, metric_expr: str, business_keys: List[str], dates: List[date]
    ) -> Dict[str, List[Tuple[date, Optional[float]]]]:
        """Track a metric value over time for records.
        
        Allows time-series analysis like "track ADA compliance score
        for sidewalk_123 from Jan-Dec 2025".
        
        Args:
            metric_expr: Field name or expression to track
            business_keys: Record identifiers
            dates: Dates to sample
            
        Returns:
            Dict mapping business_key -> [(date, value), ...]
        """
        results: Dict[str, List[Tuple[date, Optional[float]]]] = {
            bk: [] for bk in business_keys
        }
        
        for sample_date in dates:
            as_of_dt = datetime.combine(sample_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            
            for business_key in business_keys:
                record = self.get_as_of(business_key, as_of_dt)
                
                if record is None:
                    results[business_key].append((sample_date, None))
                    continue
                
                try:
                    data = record.get("data", {})
                    value = data.get(metric_expr)
                    # Try to convert to float if possible
                    if value is not None and not isinstance(value, (int, float)):
                        try:
                            value = float(value)
                        except (ValueError, TypeError):
                            value = None
                    results[business_key].append((sample_date, value))
                except Exception as e:
                    self.logger.error(f"Error tracking {metric_expr} for {business_key}: {e}")
                    results[business_key].append((sample_date, None))
        
        return results

    def detect_change_patterns(self, business_key: str) -> Optional[ChangePattern]:
        """Detect patterns in how a record has changed.
        
        Analyzes which fields change most frequently, operation sequence,
        time between changes, etc.
        
        Args:
            business_key: Record identifier
            
        Returns:
            ChangePattern or None if no versions found
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT start_date, end_date, data_values, metadata
                       FROM {sql.Identifier(self.table)}
                       WHERE business_key = %s
                       ORDER BY start_date ASC""",
                    (business_key,)
                )
                rows = cur.fetchall()
        
        if not rows:
            return None
        
        # Analyze versions
        versions = []
        fields_changed = set()
        change_types = defaultdict(int)
        
        for row in rows:
            start_date = row[0]
            data = json.loads(row[2]) if isinstance(row[2], str) else row[2]
            metadata = json.loads(row[3]) if isinstance(row[3], str) else row[3]
            
            dml_type = metadata.get("dml_type", "UNKNOWN") if metadata else "UNKNOWN"
            change_types[dml_type] += 1
            
            versions.append({
                "start_date": start_date,
                "data": data,
                "dml_type": dml_type,
            })
        
        # Track field changes
        for i in range(1, len(versions)):
            prev_data = versions[i - 1]["data"]
            curr_data = versions[i]["data"]
            
            all_keys = set(prev_data.keys()) | set(curr_data.keys())
            for key in all_keys:
                if prev_data.get(key) != curr_data.get(key):
                    fields_changed.add(key)
        
        # Calculate frequency
        first_date = versions[0]["start_date"]
        last_date = versions[-1]["start_date"]
        duration_days = (last_date - first_date).days or 1
        change_frequency = len(versions) / duration_days
        
        return ChangePattern(
            business_key=business_key,
            total_versions=len(versions),
            date_range=(first_date, last_date),
            fields_changed=fields_changed,
            change_frequency=change_frequency,
            most_recent_change=last_date,
            change_types=dict(change_types),
        )

    def get_version_count(self, business_key: str) -> int:
        """Get count of versions for a record.
        
        Args:
            business_key: Record identifier
            
        Returns:
            Number of versions
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT COUNT(*) FROM {sql.Identifier(self.table)}
                       WHERE business_key = %s""",
                    (business_key,)
                )
                return cur.fetchone()[0]

    def get_change_timeline(self, business_key: str) -> List[Dict[str, Any]]:
        """Get a timeline of all changes for a record.
        
        Returns simplified version with just change dates and types.
        
        Args:
            business_key: Record identifier
            
        Returns:
            List of change events
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT start_date, end_date, metadata
                       FROM {sql.Identifier(self.table)}
                       WHERE business_key = %s
                       ORDER BY start_date ASC""",
                    (business_key,)
                )
                rows = cur.fetchall()
        
        timeline = []
        for row in rows:
            metadata = json.loads(row[2]) if isinstance(row[2], str) else row[2]
            dml_type = metadata.get("dml_type", "UNKNOWN") if metadata else "UNKNOWN"
            
            timeline.append({
                "date": row[0].isoformat(),
                "effective_until": row[1].isoformat() if row[1] else None,
                "operation": dml_type,
            })
        
        return timeline

    def compare_versions(self, business_key: str, version1: str, version2: str) -> Dict[str, Any]:
        """Compare two specific versions of a record.
        
        Args:
            business_key: Record identifier
            version1: First scd_id
            version2: Second scd_id
            
        Returns:
            Dict with differences
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Get both versions
                cur.execute(
                    f"""SELECT data_values FROM {sql.Identifier(self.table)}
                       WHERE scd_id = %s""",
                    (version1,)
                )
                row1 = cur.fetchone()
                
                cur.execute(
                    f"""SELECT data_values FROM {sql.Identifier(self.table)}
                       WHERE scd_id = %s""",
                    (version2,)
                )
                row2 = cur.fetchone()
        
        if not row1 or not row2:
            return {"error": "One or both versions not found"}
        
        data1 = json.loads(row1[0]) if isinstance(row1[0], str) else row1[0]
        data2 = json.loads(row2[0]) if isinstance(row2[0], str) else row2[0]
        
        # Calculate diff
        all_keys = set(data1.keys()) | set(data2.keys())
        diff = {}
        
        for key in all_keys:
            val1 = data1.get(key)
            val2 = data2.get(key)
            if val1 != val2:
                diff[key] = {
                    "version1": val1,
                    "version2": val2,
                }
        
        return {
            "version1": version1,
            "version2": version2,
            "differences": diff,
            "fields_changed": len(diff),
        }

    def get_effective_date_range(self, business_key: str) -> Optional[Tuple[datetime, Optional[datetime]]]:
        """Get the complete effective date range for a record.
        
        Args:
            business_key: Record identifier
            
        Returns:
            Tuple of (first_start_date, latest_end_date) or None
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT MIN(start_date), MAX(end_date)
                       FROM {sql.Identifier(self.table)}
                       WHERE business_key = %s""",
                    (business_key,)
                )
                row = cur.fetchone()
        
        if row and row[0]:
            return (row[0], row[1])
        return None
