"""Visualization layer: Chart recommendations, dashboard generation, role-based views."""
import logging
from typing import Any, Optional

import duckdb

logger = logging.getLogger(__name__)

class ChartRecommender:
    """Recommend chart types based on column schema and data characteristics."""

    def recommend(self, schema: dict[str, Any]) -> list[dict[str, Any]]:
        """Recommend chart types for a schema.

        Args:
            schema: Schema dict with 'columns' array: [{"name": str, "type": str}, ...]

        Returns:
            List of chart recommendations: [{"type": str, "x": str, "y": str, ...}, ...]
        """
        columns = schema.get("columns", [])
        if not columns:
            return []

        col_names = [c["name"] for c in columns]
        col_types = {c["name"]: c["type"] for c in columns}

        # Find dimension and metric columns
        dimensions = [n for n in col_names if col_types.get(n) in ["VARCHAR", "STRING"]]
        metrics = [n for n in col_names if col_types.get(n) in ["INTEGER", "FLOAT", "DOUBLE", "BIGINT"]]
        timestamps = [n for n in col_names if "TIMESTAMP" in col_types.get(n, "")]

        recommendations = []

        # Time series: timestamp + metric
        if timestamps and metrics:
            recommendations.append({
                "type": "line",
                "x": timestamps[0],
                "y": metrics[0],
                "description": f"{metrics[0]} over time"
            })

        # Cross-tabulation: 2 dimensions + 1 metric
        if len(dimensions) >= 2 and metrics:
            recommendations.append({
                "type": "heatmap",
                "x": dimensions[0],
                "y": dimensions[1],
                "z": metrics[0],
                "description": f"{metrics[0]} by {dimensions[0]} × {dimensions[1]}"
            })

        # Bar chart: 1 dimension + 1 metric
        if dimensions and metrics:
            recommendations.append({
                "type": "bar",
                "x": dimensions[0],
                "y": metrics[0],
                "description": f"{metrics[0]} by {dimensions[0]}"
            })

        # Pie chart: categorical dimension (if few categories)
        if dimensions:
            recommendations.append({
                "type": "pie",
                "labels": dimensions[0],
                "values": metrics[0] if metrics else "count",
                "description": f"Distribution by {dimensions[0]}"
            })

        return recommendations if recommendations else [{"type": "table", "description": "Raw data table"}]

class DashboardGenerator:
    """Auto-generate dashboards from mart metadata."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn
        self.recommender = ChartRecommender()

    def generate(
        self,
        mart_name: str,
        title: str,
        description: str = "",
        schema: Optional[dict] = None
    ) -> dict[str, Any]:
        """Generate dashboard specification for a mart.

        Args:
            mart_name: Name of mart table (e.g., "sidewalk_repair_matrix")
            title: Dashboard title
            description: Dashboard description
            schema: Optional schema dict; if None, introspect from table

        Returns:
            Dashboard dict: {title, description, charts: [...], filters: [...], freshness: ...}
        """
        # Introspect schema if not provided
        if not schema:
            schema = self._introspect_schema(mart_name)

        # Generate chart recommendations
        charts = self.recommender.recommend(schema)

        # Extract dimensions for filters
        columns = schema.get("columns", [])
        filters = [
            {"name": c["name"], "type": c["type"]}
            for c in columns
            if c["type"] == "VARCHAR"
        ]

        dashboard = {
            "title": title,
            "description": description,
            "mart_name": mart_name,
            "charts": charts,
            "filters": filters,
            "row_count": self._get_row_count(mart_name),
            "schema": schema,
        }

        logger.info(f"Generated dashboard: {title} ({len(charts)} charts, {len(filters)} filters)")
        return dashboard

    def _introspect_schema(self, table_name: str) -> dict[str, Any]:
        """Introspect table schema from database."""
        try:
            result = self.conn.execute(f"DESCRIBE {table_name}").df()
            columns = [
                {"name": row["column_name"], "type": row["column_type"]}
                for _, row in result.iterrows()
            ]
            return {"columns": columns}
        except Exception as e:
            logger.error(f"Failed to introspect {table_name}: {e}")
            return {"columns": []}

    def _get_row_count(self, table_name: str) -> int:
        """Get row count for table."""
        try:
            result = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            return result[0] if result else 0
        except:
            return 0

class RoleBasedDashboard:
    """Filter dashboards by analyst role."""

    # Role-to-mats mapping
    ROLE_MATS = {
        "contract_analyst": [
            "sidewalk_repair_matrix",
            "construction_conflict_index",
            "raw_counts_summary",
        ],
        "ramp_analyst": [
            "ramp_completion_rates",
            "accessibility_coverage_heatmap",
            "raw_counts_summary",
        ],
        "manager": [
            "sidewalk_repair_matrix",
            "construction_conflict_index",
            "ramp_completion_rates",
            "accessibility_coverage_heatmap",
            "raw_counts_summary",
        ],
    }

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn
        self.generator = DashboardGenerator(conn)

    def get_dashboards_for_role(self, role: str) -> list[dict[str, Any]]:
        """Get dashboards visible to a specific role.

        Args:
            role: Role identifier (contract_analyst, ramp_analyst, manager)

        Returns:
            List of dashboard specifications
        """
        mart_names = self.ROLE_MATS.get(role, [])
        dashboards = []

        for mart_name in mart_names:
            try:
                # Check if mart table exists
                self.conn.execute(f"SELECT 1 FROM analytics.{mart_name} LIMIT 1")

                # Generate dashboard
                dashboard = self.generator.generate(
                    mart_name=mart_name,
                    title=self._prettify_name(mart_name),
                    description=f"Dashboard for {mart_name}"
                )
                dashboards.append(dashboard)
            except Exception as e:
                logger.warning(f"Skipping {mart_name} for role {role}: {e}")

        logger.info(f"Generated {len(dashboards)} dashboards for role: {role}")
        return dashboards

    @staticmethod
    def _prettify_name(name: str) -> str:
        """Convert snake_case to Title Case."""
        return " ".join(word.capitalize() for word in name.split("_"))
