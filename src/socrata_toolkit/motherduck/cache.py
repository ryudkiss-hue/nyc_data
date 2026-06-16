"""Cloud Cache Management for MotherDuck."""

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

class CloudCacheManager:
    """
    Manages L3 cloud cache on MotherDuck with 12-month retention policy.

    Features:
    - Track last fetch time per dataset
    - Incremental delta sync (only fetch updated rows)
    - Archive old records (soft delete)
    - Calculate cache hit rates
    """

    RETENTION_DAYS = 365  # 12-month retention

    def __init__(self, client):
        """
        Initialize cloud cache manager.

        Args:
            client: MotherDuckClient instance
        """
        self.client = client

    def get_last_fetch_time(self, dataset_key: str) -> Optional[datetime]:
        """
        Get last fetch timestamp for a dataset.

        Args:
            dataset_key: Dataset identifier

        Returns:
            Last fetch datetime or None if never fetched
        """
        sql = f"""
            SELECT MAX(fetched_at)
            FROM raw_cloud.fetch_metadata
            WHERE dataset_key = '{dataset_key}'
        """
        try:
            result = self.client.query(sql)
            if result and result[0][0]:
                return result[0][0]
            return None
        except Exception as e:
            logger.warning(f"Failed to get last fetch time: {e}")
            return None

    def record_fetch(
        self,
        dataset_key: str,
        row_count: int,
        source_fourfour: str,
        fetch_time: datetime,
    ) -> bool:
        """
        Record fetch event for delta tracking.

        Args:
            dataset_key: Dataset identifier
            row_count: Rows fetched
            source_fourfour: Socrata dataset ID
            fetch_time: When fetch occurred

        Returns:
            Success status
        """
        sql = f"""
            INSERT INTO raw_cloud.fetch_metadata
            (dataset_key, source_fourfour, row_count, fetched_at)
            VALUES ('{dataset_key}', '{source_fourfour}', {row_count}, '{fetch_time.isoformat()}')
        """
        try:
            self.client.query(sql)
            logger.info(f"Recorded fetch: {dataset_key} ({row_count} rows)")
            return True
        except Exception as e:
            logger.error(f"Failed to record fetch: {e}")
            return False

    def archive_old_records(self, dataset_key: str) -> int:
        """
        Soft-delete records older than retention period.

        Args:
            dataset_key: Dataset identifier

        Returns:
            Count of archived records
        """
        cutoff = datetime.now() - timedelta(days=self.RETENTION_DAYS)
        sql = f"""
            UPDATE raw_cloud.{dataset_key}
            SET archived = TRUE
            WHERE fetched_at < '{cutoff.isoformat()}'
                AND archived = FALSE
        """
        try:
            self.client.query(sql)
            # Get count of archived
            count_sql = f"""
                SELECT COUNT(*)
                FROM raw_cloud.{dataset_key}
                WHERE archived = TRUE
            """
            result = self.client.query(count_sql)
            archived_count = result[0][0] if result else 0
            logger.info(f"Archived {archived_count} old records from {dataset_key}")
            return archived_count
        except Exception as e:
            logger.error(f"Failed to archive old records: {e}")
            return 0

    def get_cache_stats(self) -> dict[str, any]:
        """
        Get cache statistics (sizes, hits, freshness).

        Returns:
            Dictionary with cache metrics
        """
        sql = """
            SELECT
                dataset_key,
                COUNT(*) as total_rows,
                COUNT(CASE WHEN archived = FALSE THEN 1 END) as active_rows,
                MAX(fetched_at) as last_fetch
            FROM raw_cloud.datasets
            GROUP BY dataset_key
        """
        try:
            results = self.client.query(sql)
            stats = {
                "datasets": len(results),
                "total_rows": sum(r[1] for r in results),
                "active_rows": sum(r[2] for r in results),
            }
            logger.info(f"Cache stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"datasets": 0, "total_rows": 0, "active_rows": 0}

    def calculate_sync_window(self, dataset_key: str) -> Optional[str]:
        """
        Calculate delta fetch window (last_fetch_time to now).

        Args:
            dataset_key: Dataset identifier

        Returns:
            SOQL where clause for delta fetch
        """
        last_fetch = self.get_last_fetch_time(dataset_key)
        if not last_fetch:
            return None  # Full fetch on first run

        return f"updated_at > '{last_fetch.isoformat()}'"
