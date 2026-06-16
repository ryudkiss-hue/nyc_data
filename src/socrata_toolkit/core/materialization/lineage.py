"""Data lineage tracking: datasets → marts."""
import json
import logging
from datetime import datetime

import duckdb

logger = logging.getLogger(__name__)

class MartLineage:
    """Track data lineage: which datasets feed which marts."""

    def __init__(self):
        self.lineage_table = "analytics._lineage"

    def _ensure_table(self, conn: duckdb.DuckDBPyConnection):
        """Create lineage table if not exists."""
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.lineage_table} (
                mart_name VARCHAR,
                source_datasets VARCHAR,
                target_schema VARCHAR,
                target_table VARCHAR,
                row_count INTEGER,
                materialized_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

    def record(
        self,
        mart_name: str,
        source_datasets: list,
        target_schema: str,
        target_table: str,
        row_count: int,
        conn: duckdb.DuckDBPyConnection,
    ):
        """Record lineage for a materialized mart."""
        self._ensure_table(conn)

        try:
            conn.execute(
                f"""
                INSERT INTO {self.lineage_table}
                (mart_name, source_datasets, target_schema, target_table, row_count, materialized_at)
                VALUES (?, ?, ?, ?, ?, NOW())
                """,
                [
                    mart_name,
                    json.dumps(source_datasets),
                    target_schema,
                    target_table,
                    row_count,
                ],
            )
            logger.info(f"Recorded lineage: {mart_name} ← {source_datasets}")
        except Exception as e:
            logger.error(f"Failed to record lineage for {mart_name}: {e}")

    def get_upstream(self, mart_name: str, conn: duckdb.DuckDBPyConnection) -> list:
        """Get datasets that feed this mart."""
        try:
            result = conn.execute(
                f"SELECT source_datasets FROM {self.lineage_table} WHERE mart_name = ? ORDER BY materialized_at DESC LIMIT 1",
                [mart_name],
            ).fetchone()
            if result:
                return json.loads(result[0])
            return []
        except:
            return []

    def get_downstream(self, dataset_key: str, conn: duckdb.DuckDBPyConnection) -> list:
        """Get mats that use this dataset."""
        try:
            results = conn.execute(
                f"SELECT DISTINCT mart_name FROM {self.lineage_table} WHERE source_datasets LIKE ?"
            ).fetchall()
            return [r[0] for r in results]
        except:
            return []
