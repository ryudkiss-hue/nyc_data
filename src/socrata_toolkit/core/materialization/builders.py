"""Specific builder implementations for common mart patterns."""
import logging
from typing import Optional

import duckdb

from .builder import MartBuilder
from .registry import BuilderRegistry

logger = logging.getLogger(__name__)


@BuilderRegistry.register("universal_counts")
class UniversalCountsBuilder(MartBuilder):
    """Universal mart: row counts for all datasets.

    Produces one row per dataset:
        dataset | row_count | materialized_at
    """

    def build_sql(self) -> str:
        """Generate UNION query for all datasets."""
        queries = []

        # Get list of datasets (from config["datasets"] == "all" means iterate staging)
        try:
            # Query information_schema to find all staging tables
            tables = self.conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'staging'"
            ).fetchall()
            staging_tables = [t[0] for t in tables]
        except:
            logger.error("Failed to list staging tables")
            return None

        for table_name in staging_tables:
            queries.append(
                f"SELECT '{table_name}' as dataset, COUNT(*) as row_count, NOW() as materialized_at FROM staging.{table_name}"
            )

        if not queries:
            logger.error("No staging tables found for universal_counts")
            return None

        return " UNION ALL ".join(queries)


@BuilderRegistry.register("cross_tab")
class CrossTabBuilder(MartBuilder):
    """Cross-tabulation builder: rows × columns with metric aggregation.

    Example: Material × Borough with COUNT(*) → sidewalk_repair_matrix
    """

    def build_sql(self) -> str:
        """Generate cross-tab SQL from config."""
        row_col_name = self.mat_config.get("rows")
        col_col_name = self.mat_config.get("cols")
        metric = self.mat_config.get("metric", "COUNT(*)")

        if not row_col_name or not col_col_name:
            logger.error("cross_tab requires 'rows' and 'cols' in config")
            return None

        queries = []

        # Generate for each dataset
        for dataset_key in self.datasets:
            if dataset_key == "all":
                continue

            if dataset_key not in self.discovered_columns:
                logger.warning(f"No discovered columns for {dataset_key}; skipping")
                continue

            actual_cols = self.discovered_columns[dataset_key]["actual_columns"]

            # Find actual column names
            row_col = self._pick_column([row_col_name], actual_cols)
            col_col = self._pick_column([col_col_name], actual_cols)

            if not row_col or not col_col:
                logger.warning(
                    f"Could not find {row_col_name} or {col_col_name} in {dataset_key}; skipping"
                )
                continue

            # Generate query for this dataset
            query = f"""
            SELECT
              '{dataset_key}' as dataset,
              "{row_col}" as row_val,
              "{col_col}" as col_val,
              {metric} as metric_value
            FROM staging.{dataset_key}
            GROUP BY "{row_col}", "{col_col}"
            """
            queries.append(query)

        if not queries:
            logger.error(f"cross_tab: No valid datasets for {self.mat_name}")
            return None

        return " UNION ALL ".join(queries)


@BuilderRegistry.register("completion_rate")
class CompletionRateBuilder(MartBuilder):
    """Completion rate builder: numerator/denominator with Wilson Score CI.

    Example: Ramps completed / ramps total by borough → ramp_completion_rates
    """

    def build_sql(self) -> str:
        """Generate completion rate + CI SQL."""
        numerator_filter = self.mat_config.get("numerator_filter", "status = 'completed'")
        denominator_filter = self.mat_config.get("denominator_filter", "1=1")
        group_by = self.mat_config.get("group_by", "borough")

        queries = []

        for dataset_key in self.datasets:
            if dataset_key == "all":
                continue

            if dataset_key not in self.discovered_columns:
                logger.warning(f"No discovered columns for {dataset_key}; skipping")
                continue

            # Find borough column
            actual_cols = self.discovered_columns[dataset_key]["actual_columns"]
            borough_col = self._pick_column(["borough", "borough_code", "boro"], actual_cols)

            if not borough_col:
                logger.warning(f"Could not find borough column in {dataset_key}; skipping")
                continue

            query = f"""
            WITH rates AS (
              SELECT
                '{dataset_key}' as dataset,
                "{borough_col}" as borough,
                SUM(CASE WHEN {numerator_filter} THEN 1 ELSE 0 END)::FLOAT as completed,
                COUNT(*) as total
              FROM staging.{dataset_key}
              WHERE {denominator_filter}
              GROUP BY "{borough_col}"
            )
            SELECT
              dataset,
              borough,
              completed / total as completion_rate,
              ROUND(100 * completed / total, 2) as completion_pct
            FROM rates
            """
            queries.append(query)

        if not queries:
            logger.error(f"completion_rate: No valid datasets for {self.mat_name}")
            return None

        return " UNION ALL ".join(queries)
