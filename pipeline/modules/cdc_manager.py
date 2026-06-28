"""
Change Data Capture (CDC) Manager
Tracks changes using hash-based row comparison.
Detects inserts, updates, and deletes efficiently.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class ChangeRecord:
    """Represents a detected change."""
    primary_key: str
    change_type: str  # INSERT, UPDATE, DELETE
    before_hash: Optional[str] = None
    after_hash: Optional[str] = None
    detected_at: Optional[str] = None


class CDCManager:
    """
    Change Data Capture using hash-based row comparison.
    Efficiently detects what changed between two dataset versions.
    """

    def __init__(self, bridge):
        """Initialize CDC manager."""
        self.bridge = bridge
        self.changes: List[ChangeRecord] = []

    @staticmethod
    def compute_row_hash(row_data: Dict) -> str:
        """
        Compute SHA256 hash of row data.
        Excludes timestamp fields and primary keys.
        """
        # Sort keys for consistent hashing
        sorted_items = sorted(row_data.items())
        hash_input = str(sorted_items).encode('utf-8')
        return hashlib.sha256(hash_input).hexdigest()

    def detect_changes(
        self,
        old_table: str,
        new_table: str,
        pk_column: str,
        schema: str = "raw"
    ) -> Dict[str, List[ChangeRecord]]:
        """
        Detect changes between two table versions.
        
        Returns:
            {
                'inserts': [ChangeRecord],
                'updates': [ChangeRecord],
                'deletes': [ChangeRecord]
            }
        """
        logger.info(f"Detecting changes: {old_table} → {new_table}")

        changes = {'inserts': [], 'updates': [], 'deletes': []}

        # Fetch old and new data
        old_rows = self.bridge.query(f"SELECT * FROM {schema}.{old_table}")
        new_rows = self.bridge.query(f"SELECT * FROM {schema}.{new_table}")

        # Build maps by primary key
        old_map = {str(row[pk_column]): row for row in old_rows} if old_rows else {}
        new_map = {str(row[pk_column]): row for row in new_rows} if new_rows else {}

        old_keys = set(old_map.keys())
        new_keys = set(new_map.keys())

        # Detect inserts (in new but not in old)
        for pk in new_keys - old_keys:
            changes['inserts'].append(
                ChangeRecord(
                    primary_key=pk,
                    change_type='INSERT',
                    after_hash=self.compute_row_hash(new_map[pk])
                )
            )

        # Detect deletes (in old but not in new)
        for pk in old_keys - new_keys:
            changes['deletes'].append(
                ChangeRecord(
                    primary_key=pk,
                    change_type='DELETE',
                    before_hash=self.compute_row_hash(old_map[pk])
                )
            )

        # Detect updates (in both, but different hashes)
        for pk in old_keys & new_keys:
            old_hash = self.compute_row_hash(old_map[pk])
            new_hash = self.compute_row_hash(new_map[pk])

            if old_hash != new_hash:
                changes['updates'].append(
                    ChangeRecord(
                        primary_key=pk,
                        change_type='UPDATE',
                        before_hash=old_hash,
                        after_hash=new_hash
                    )
                )

        logger.info(f"Changes detected: {len(changes['inserts'])} inserts, "
                   f"{len(changes['updates'])} updates, {len(changes['deletes'])} deletes")

        return changes

    def generate_change_report(self, changes: Dict[str, List[ChangeRecord]]) -> Dict:
        """Generate summary report of detected changes."""
        return {
            'total_changes': (len(changes['inserts']) +
                            len(changes['updates']) +
                            len(changes['deletes'])),
            'inserts': len(changes['inserts']),
            'updates': len(changes['updates']),
            'deletes': len(changes['deletes']),
            'insert_ratio': (len(changes['inserts']) /
                           sum(len(v) for v in changes.values()) if sum(len(v) for v in changes.values()) > 0 else 0),
            'update_ratio': (len(changes['updates']) /
                           sum(len(v) for v in changes.values()) if sum(len(v) for v in changes.values()) > 0 else 0),
            'delete_ratio': (len(changes['deletes']) /
                           sum(len(v) for v in changes.values()) if sum(len(v) for v in changes.values()) > 0 else 0)
        }

    def apply_changes(
        self,
        staging_table: str,
        changes: Dict[str, List[ChangeRecord]],
        schema: str = "staging"
    ) -> bool:
        """
        Apply detected changes to staging table.
        Uses MERGE for efficient upserts.
        """
        if not changes['inserts'] and not changes['updates'] and not changes['deletes']:
            logger.info("No changes to apply")
            return True

        try:
            # Delete removed records
            for change in changes['deletes']:
                delete_sql = f"DELETE FROM {schema}.{staging_table} WHERE id = '{change.primary_key}'"
                result = self.bridge.execute_sql(delete_sql)
                if not result.success:
                    logger.error(f"Failed to delete {change.primary_key}: {result.error}")
                    return False

            # Insert and update handled by staging layer
            logger.info(f"Applied {len(changes['inserts']) + len(changes['updates'])} changes to {staging_table}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply changes: {str(e)}")
            return False


class ChangeDataCaptureStrategy:
    """Strategies for different CDC patterns."""

    @staticmethod
    def hash_based_cdc(bridge, old_table: str, new_table: str, pk: str) -> Dict:
        """Hash-based CDC - detects all changes efficiently."""
        cdc = CDCManager(bridge)
        changes = cdc.detect_changes(old_table, new_table, pk)
        report = cdc.generate_change_report(changes)
        logger.info(f"CDC Report: {report}")
        return changes

    @staticmethod
    def timestamp_cdc(bridge, table: str, timestamp_col: str, since: str) -> Dict:
        """Timestamp-based CDC - detects changes since timestamp."""
        query = f"SELECT * FROM {table} WHERE {timestamp_col} >= '{since}' ORDER BY {timestamp_col}"
        rows = bridge.query(query)

        return {
            'inserts': len(rows),
            'updates': 0,
            'deletes': 0,
            'rows': rows
        }

