"""Base builder class for all mart materialization patterns."""
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import duckdb

logger = logging.getLogger(__name__)


class MartBuilder(ABC):
    """Abstract base class for all mart builders.

    Each builder generates and executes SQL to materialize a specific mart
    from staging tables. Builders discover columns dynamically from dataset configs.
    """

    def __init__(self, mat_config: dict, dataset_configs: dict, conn: duckdb.DuckDBPyConnection):
        """Initialize builder.

        Args:
            mat_config: Mart definition from analytics_config.json (name, builder, datasets, params)
            dataset_configs: All dataset configurations from dataset_config.json
            conn: DuckDB connection
        """
        self.mat_config = mat_config
        self.dataset_configs = dataset_configs
        self.conn = conn
        self.mat_name = mat_config["name"]
        self.datasets = mat_config.get("datasets", [])
        self.discovered_columns = {}

        # Discover columns for each dataset
        self._discover_columns()

    def _discover_columns(self):
        """Discover actual columns in staging tables using DESCRIBE and config hints."""
        for dataset_key in self.datasets:
            if dataset_key == "all":
                continue  # Handle "all" separately in builder

            try:
                # Get actual columns from staging table
                staging_table = f"staging.{dataset_key}"
                if not self._table_exists(staging_table):
                    logger.warning(f"Staging table {staging_table} not found; skipping")
                    continue

                # Describe the table
                columns_df = self.conn.execute(f"DESCRIBE {staging_table}").df()
                actual_columns = set(columns_df["column_name"].tolist())

                # Get config hints for this dataset
                dataset_config = self.dataset_configs.get(dataset_key, {})
                self.discovered_columns[dataset_key] = {
                    "actual_columns": actual_columns,
                    "config": dataset_config,
                }
            except Exception as e:
                logger.error(f"Failed to discover columns for {dataset_key}: {e}")
                self.discovered_columns[dataset_key] = {"actual_columns": set(), "config": {}}

    def _table_exists(self, table_name: str) -> bool:
        """Check if table exists."""
        try:
            self.conn.execute(f"SELECT 1 FROM {table_name} LIMIT 1")
            return True
        except:
            return False

    def _pick_column(self, candidates: List[str], actual_columns: set) -> Optional[str]:
        """Pick first candidate that exists in actual columns."""
        for candidate in candidates:
            if candidate in actual_columns:
                return candidate
        return None

    @abstractmethod
    def build_sql(self) -> str:
        """Generate SQL for this mart. Subclasses override."""
        pass

    def materialize(self, schema: str = "analytics") -> dict:
        """Materialize the mart (idempotent: DROP and CREATE).

        Args:
            schema: Target schema (analytics, validation, monitoring, etc.)

        Returns:
            Status dict: {"status": "success|error|partial", "table": "...", "row_count": N, ...}
        """
        target_table = f"{schema}.{self.mat_name}"

        try:
            # Ensure schema exists
            self.conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

            # Generate SQL
            sql = self.build_sql()
            if not sql:
                return {
                    "status": "error",
                    "error": "Builder failed to generate SQL",
                    "table": target_table,
                }

            # Drop existing table/view (idempotent)
            self._drop_target(target_table)

            # Create new table
            self.conn.execute(f"CREATE TABLE {target_table} AS {sql}")

            # Get row count
            row_count = self.conn.execute(f"SELECT COUNT(*) FROM {target_table}").fetchone()[0]

            logger.info(f"Materialized {target_table}: {row_count} rows")

            return {
                "status": "success",
                "table": target_table,
                "row_count": row_count,
                "datasets": self.datasets,
            }
        except Exception as e:
            logger.error(f"Failed to materialize {target_table}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "table": target_table,
            }

    def _drop_target(self, target_table: str):
        """Drop table if exists (handles both TABLE and VIEW types)."""
        try:
            self.conn.execute(f"DROP TABLE IF EXISTS {target_table}")
        except:
            try:
                self.conn.execute(f"DROP VIEW IF EXISTS {target_table}")
            except:
                pass  # Table/View doesn't exist
