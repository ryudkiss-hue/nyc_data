"""Audit logging framework for data validation checks.

Provides audit trail capability for all data quality checks with JSON export
and DuckDB persistence for compliance and monitoring.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    """Represents a single audit log entry for a validation check.

    Attributes:
        timestamp: When the check was performed (ISO 8601)
        check_type: Type of validation (uniqueness, freshness, counts, business_rules)
        table_name: The table being validated
        run_id: Unique identifier for this validation run
        status: Result status (success, failure, warning, skipped, error)
        rows_affected: Number of rows checked
        details: Additional context (error messages, metric values, etc.)
        audit_id: Unique identifier for this audit entry
    """
    timestamp: str
    check_type: str
    table_name: str
    run_id: str
    status: str
    rows_affected: int
    details: Dict[str, Any]
    audit_id: str = field(default_factory=lambda: str(uuid4()))


class AuditLogger:
    """Captures and manages audit logs for data validation operations.

    Enables comprehensive tracking of all validation checks, including failures,
    successes, warnings, and edge cases. Supports JSON export and DuckDB persistence.
    """

    def __init__(self, run_id: Optional[str] = None):
        """Initialize the audit logger.

        Args:
            run_id: Optional run identifier. If not provided, a new UUID is generated.
        """
        self.run_id = run_id or str(uuid4())
        self.entries: List[AuditEntry] = []
        logger.info(f"AuditLogger initialized with run_id={self.run_id}")

    def log_check(
        self,
        check_type: str,
        table_name: str,
        status: str,
        rows_affected: int = 0,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEntry:
        """Log a single validation check result.

        Args:
            check_type: Type of validation (uniqueness, freshness, counts, business_rules)
            table_name: Name of the table being validated
            status: Result status (success, failure, warning, skipped, error)
            rows_affected: Number of rows affected by this check
            details: Additional context and metrics from the check

        Returns:
            The created AuditEntry
        """
        if details is None:
            details = {}

        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            check_type=check_type,
            table_name=table_name,
            run_id=self.run_id,
            status=status,
            rows_affected=rows_affected,
            details=details
        )

        self.entries.append(entry)
        logger.info(
            f"Logged {check_type} check for {table_name}: {status} "
            f"({rows_affected} rows affected)"
        )
        return entry

    def to_json(self) -> str:
        """Export all audit entries as JSON string.

        Returns:
            JSON representation of all audit entries
        """
        entries_dicts = [asdict(entry) for entry in self.entries]
        return json.dumps(entries_dicts, indent=2, default=str)

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Export all audit entries as list of dictionaries.

        Returns:
            List of dictionaries representing audit entries
        """
        return [asdict(entry) for entry in self.entries]

    def save_to_duckdb(self, conn, audit_table: str = "audit_logs") -> bool:
        """Persist audit logs to DuckDB.

        Creates the audit table if it doesn't exist, then inserts all entries.

        Args:
            conn: DuckDB connection
            audit_table: Name of the table to create/use (default: audit_logs)

        Returns:
            True if save was successful, False otherwise
        """
        if not self.entries:
            logger.warning("No audit entries to save")
            return False

        try:
            # Create table if it doesn't exist
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {audit_table} (
                    audit_id VARCHAR,
                    timestamp VARCHAR,
                    check_type VARCHAR,
                    table_name VARCHAR,
                    run_id VARCHAR,
                    status VARCHAR,
                    rows_affected INTEGER,
                    details JSON,
                    PRIMARY KEY (audit_id)
                )
            """)

            # Insert entries
            for entry in self.entries:
                details_json = json.dumps(entry.details)
                conn.execute(f"""
                    INSERT INTO {audit_table}
                    (audit_id, timestamp, check_type, table_name, run_id, status, rows_affected, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    entry.audit_id,
                    entry.timestamp,
                    entry.check_type,
                    entry.table_name,
                    entry.run_id,
                    entry.status,
                    entry.rows_affected,
                    details_json
                ])

            logger.info(f"Successfully saved {len(self.entries)} audit entries to {audit_table}")
            return True

        except Exception as e:
            logger.error(f"Failed to save audit logs to DuckDB: {e}")
            return False

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of audit log statistics.

        Returns:
            Dictionary with summary statistics
        """
        status_counts = {}
        check_type_counts = {}
        total_rows_affected = 0

        for entry in self.entries:
            status_counts[entry.status] = status_counts.get(entry.status, 0) + 1
            check_type_counts[entry.check_type] = check_type_counts.get(entry.check_type, 0) + 1
            total_rows_affected += entry.rows_affected

        return {
            "run_id": self.run_id,
            "total_entries": len(self.entries),
            "status_counts": status_counts,
            "check_type_counts": check_type_counts,
            "total_rows_affected": total_rows_affected,
            "timestamp_range": {
                "start": self.entries[0].timestamp if self.entries else None,
                "end": self.entries[-1].timestamp if self.entries else None
            }
        }

    def filter_by_status(self, status: str) -> List[AuditEntry]:
        """Get all entries with a specific status.

        Args:
            status: Status to filter by (success, failure, warning, skipped, error)

        Returns:
            List of matching entries
        """
        return [entry for entry in self.entries if entry.status == status]

    def filter_by_check_type(self, check_type: str) -> List[AuditEntry]:
        """Get all entries for a specific check type.

        Args:
            check_type: Check type to filter by

        Returns:
            List of matching entries
        """
        return [entry for entry in self.entries if entry.check_type == check_type]

    def filter_by_table(self, table_name: str) -> List[AuditEntry]:
        """Get all entries for a specific table.

        Args:
            table_name: Table name to filter by

        Returns:
            List of matching entries
        """
        return [entry for entry in self.entries if entry.table_name == table_name]
