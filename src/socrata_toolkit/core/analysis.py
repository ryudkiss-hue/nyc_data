"""Analysis layer: Pre-built queries, NL interface, statistical summaries."""
import logging
from datetime import datetime
<<<<<<< HEAD
from typing import Any, Optional
=======
from typing import Any, Dict, List, Optional
>>>>>>> main

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

class AnalyticalQueryTemplate:
    """Pre-built analytical query templates for common questions."""

    def __init__(self, name: str, mart_name: str, description: str, query: str):
        """Initialize query template.

        Args:
            name: Template identifier (e.g., "top_materials_by_borough")
            mart_name: Which mart this query applies to
            description: Human-readable description
            query: SQL template (can use {mart} placeholder)
        """
        self.name = name
        self.mart_name = mart_name
        self.description = description
        self.query = query

    def render(self, **kwargs) -> str:
        """Render query with parameters."""
        return self.query.format(mart=self.mart_name, **kwargs)

class StatisticalSummary:
    """Compute statistical summaries (mean, median, CI, outliers) for mart columns."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def compute(self, table: str, columns: list[str]) -> dict[str, Any]:
        """Compute statistics for specified columns.

        Args:
            table: Table name (e.g., "analytics.sidewalk_repair_matrix")
            columns: Column names to summarize

        Returns:
            Dict mapping column names to their statistics
        """
        results = {}

        for col in columns:
            try:
                # Check column type
                col_type = self._get_column_type(table, col)

                if col_type in ["INTEGER", "FLOAT", "DOUBLE", "BIGINT"]:
                    results[col] = self._numeric_stats(table, col)
                else:
                    results[col] = self._categorical_stats(table, col)
            except Exception as e:
                logger.error(f"Failed to compute stats for {col}: {e}")
                results[col] = {"error": str(e)}

        return results

    def _get_column_type(self, table: str, col: str) -> str:
        """Get column data type."""
        result = self.conn.execute(f"DESCRIBE {table}").df()
        col_info = result[result["column_name"] == col]
        if col_info.empty:
            raise ValueError(f"Column {col} not found in {table}")
        return col_info.iloc[0]["column_type"]

    def _numeric_stats(self, table: str, col: str) -> dict[str, float]:
        """Compute numeric statistics (mean, median, stddev, min, max, quartiles)."""
        query = f"""
        SELECT
          COUNT(*) as count,
          AVG("{col}") as mean,
          MEDIAN("{col}") as median,
          STDDEV("{col}") as stddev,
          MIN("{col}") as min,
          MAX("{col}") as max,
          QUANTILE_CONT("{col}", 0.25) as q1,
          QUANTILE_CONT("{col}", 0.75) as q3
        FROM {table}
        WHERE "{col}" IS NOT NULL
        """
        result = self.conn.execute(query).fetchall()
        if result:
            row = result[0]
            return {
                "count": row[0],
                "mean": float(row[1]) if row[1] else None,
                "median": float(row[2]) if row[2] else None,
                "stddev": float(row[3]) if row[3] else None,
                "min": float(row[4]) if row[4] else None,
                "max": float(row[5]) if row[5] else None,
                "q1": float(row[6]) if row[6] else None,
                "q3": float(row[7]) if row[7] else None,
            }
        return {}

    def _categorical_stats(self, table: str, col: str) -> dict[str, Any]:
        """Compute categorical statistics (top categories, distribution)."""
        query = f"""
        SELECT
          "{col}" as value,
          COUNT(*) as count
        FROM {table}
        WHERE "{col}" IS NOT NULL
        GROUP BY "{col}"
        ORDER BY count DESC
        LIMIT 10
        """
        result = self.conn.execute(query).fetchall()
        top_categories = [{"value": row[0], "count": row[1]} for row in result]

        total = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

        return {
            "top_categories": top_categories,
            "total_distinct": len(top_categories),
            "total_rows": total,
        }

class AnalysisEngine:
    """Execute pre-built queries, handle NL queries, track query history."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn
        self.query_history = []
        self.query_templates: dict[str, AnalyticalQueryTemplate] = {}

    def register_template(self, template: AnalyticalQueryTemplate):
        """Register a query template."""
        self.query_templates[template.name] = template
        logger.info(f"Registered query template: {template.name}")

    def execute_query(self, sql: str, label: str = None) -> Optional[pd.DataFrame]:
        """Execute a SQL query and track it.

        Args:
            sql: SQL query to execute
            label: Optional label for tracking

        Returns:
            Result as DataFrame or None if error
        """
        try:
            result = self.conn.execute(sql).df()

            self.query_history.append({
                "sql": sql,
                "label": label,
                "timestamp": datetime.now().isoformat(),
                "row_count": len(result),
                "status": "success",
            })

            logger.info(f"Executed query: {label or 'unnamed'} ({len(result)} rows)")
            return result
        except Exception as e:
            self.query_history.append({
                "sql": sql,
                "label": label,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "status": "error",
            })

            logger.error(f"Query failed: {e}")
            return None

    def execute_template(self, template_name: str, **kwargs) -> Optional[pd.DataFrame]:
        """Execute a registered query template.

        Args:
            template_name: Name of registered template
            **kwargs: Parameters to render template

        Returns:
            Result as DataFrame
        """
        if template_name not in self.query_templates:
            logger.error(f"Template not found: {template_name}")
            return None

        template = self.query_templates[template_name]
        sql = template.render(**kwargs)
        return self.execute_query(sql, label=template_name)

    def get_query_history(self) -> list[dict]:
        """Get query execution history."""
        return self.query_history.copy()

    def clear_history(self):
        """Clear query history."""
        self.query_history.clear()
