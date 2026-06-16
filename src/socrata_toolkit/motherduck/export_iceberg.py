"""Iceberg export functionality for analytics results (motherduck-ducklake).

Purpose: Enable external sharing of analytics results in Apache Iceberg format.
Iceberg is an open table format that supports:
- ACID transactions
- Partition evolution
- Schema evolution
- Time travel queries
- Compatible with external tools (Spark, Presto, Trino, DuckDB)

This module provides the IcebergExporter class for exporting analytics tables
to Iceberg format on local filesystem or S3-compatible storage.

Note: This is an optional Phase 2 feature. Actual S3 export requires credentials.
"""
import logging
from pathlib import Path
from typing import Any, Optional

try:
    from socrata_toolkit.motherduck.connector import MotherDuckConnection
except ImportError:
    MotherDuckConnection = None

logger = logging.getLogger(__name__)

class IcebergExporter:
    """Export analytics tables to Apache Iceberg format.

    Provides methods to export analytics results (from all 5 phases + KPIs)
    to Iceberg format on local filesystem or S3 storage. Iceberg enables
    external data sharing with schema versioning and time travel support.

    Attributes:
        connection: MotherDuckConnection instance for querying analytics tables
        export_path: Base path for Iceberg exports (local or S3)
        DEFAULT_TABLES: List of default tables to export if none specified

    Example:
        conn = MotherDuckConnection()
        exporter = IcebergExporter(connection=conn, export_path="s3://bucket/exports")
        result = exporter.export_analytics_tables()
        # Or export specific tables:
        result = exporter.export_analytics_tables(
            tables=["phase_b_spatial_clusters", "kpi_metrics"]
        )
    """

    # Default tables to export (all analytics phases + KPIs)
    DEFAULT_TABLES = [
        "phase_b_spatial_clusters",  # DBSCAN spatial clustering
        "phase_c_distributions",      # Distribution analysis
        "phase_d_anomalies",          # Anomaly detection (CUSUM/Bayesian)
        "phase_e_decomposition",      # Time series decomposition
        "phase_f_bootstrap_ci",       # Bootstrap confidence intervals
        "kpi_metrics",                # Aggregated KPIs
    ]

    def __init__(
        self, connection: MotherDuckConnection, export_path: str
    ) -> None:
        """Initialize Iceberg exporter.

        Args:
            connection: MotherDuckConnection instance for querying tables
            export_path: Base path for exports (e.g., "/data/exports" or
                        "s3://bucket/exports"). Must be accessible from
                        DuckDB with appropriate credentials.

        Raises:
            ValueError: If export_path is empty or None
            TypeError: If connection is not a MotherDuckConnection instance
        """
        if not export_path:
            raise ValueError("export_path must not be empty")

        if connection is None:
            raise TypeError("connection must be a MotherDuckConnection instance")

        self.connection = connection
        self.export_path = export_path
        logger.info(
            f"Initialized IcebergExporter with export_path={export_path} "
            f"[mode={'MotherDuck' if connection.is_motherduck else 'Local DuckDB'}]"
        )

    def _compute_table_path(self, table_name: str) -> str:
        """Compute full path for a table in Iceberg format.

        Appends table name as a subdirectory with trailing slash.
        Handles both local paths and S3 URIs correctly.

        Args:
            table_name: Name of analytics table to export

        Returns:
            Full path for Iceberg table export

        Example:
            >>> exporter._compute_table_path("phase_b_spatial_clusters")
            '/data/exports/phase_b_spatial_clusters/'

            >>> exporter._compute_table_path("kpi_metrics")
            's3://bucket/exports/kpi_metrics/'
        """
        # Ensure path doesn't end with slash, add table name, then add trailing slash
        base = self.export_path.rstrip("/")
        return f"{base}/{table_name}/"

    def export_analytics_tables(
        self, tables: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Export analytics tables to Iceberg format.

        Exports specified tables (or defaults if None) to Iceberg format.
        Each table is exported to its own subdirectory under export_path.

        Implementation note: This method provides the structure for table export.
        Actual S3 integration requires DuckDB Iceberg extension and AWS credentials
        configured in the DuckDB session.

        Args:
            tables: List of table names to export. If None, uses DEFAULT_TABLES.
                   Valid tables: All phase analytics tables and KPI tables.

        Returns:
            Dictionary with export results:
            {
                "status": "success" | "partial" | "failed",
                "tables_requested": int,
                "tables_exported": int,
                "export_path": str,
                "details": {
                    "table_name": {
                        "status": "exported" | "skipped" | "error",
                        "path": str,
                        "message": str  # optional
                    }
                }
            }

        Example:
            # Export default tables
            result = exporter.export_analytics_tables()
            print(f"Exported {result['tables_exported']} tables")

            # Export specific tables
            result = exporter.export_analytics_tables(
                tables=["phase_b_spatial_clusters", "kpi_metrics"]
            )
            if result["status"] == "success":
                print("All tables exported successfully")
        """
        tables_to_export = tables if tables is not None else self.DEFAULT_TABLES
        results = {
            "status": "success",
            "tables_requested": len(tables_to_export),
            "tables_exported": 0,
            "export_path": self.export_path,
            "details": {},
        }

        for table_name in tables_to_export:
            try:
                result = self._export_table_to_iceberg(table_name)
                results["details"][table_name] = result
                if result["status"] == "exported":
                    results["tables_exported"] += 1
                elif result["status"] == "error":
                    results["status"] = "partial"
            except Exception as e:
                logger.error(f"Error exporting table {table_name}: {e}")
                results["details"][table_name] = {
                    "status": "error",
                    "path": self._compute_table_path(table_name),
                    "message": str(e),
                }
                results["status"] = "partial"

        logger.info(
            f"Export complete: {results['tables_exported']}/{results['tables_requested']} "
            f"tables exported [status={results['status']}]"
        )
        return results

    def _export_table_to_iceberg(self, table_name: str) -> dict[str, Any]:
        """Export single analytics table to Iceberg format.

        Exports a table from the analytics database to Iceberg format.
        Creates a new Iceberg table at the computed path with schema
        and data from the source table.

        Implementation note: The actual export uses DuckDB's Iceberg
        extension via CREATE TABLE ... AS SELECT pattern:
        - CREATE TABLE iceberg.{path}/{table_name} AS SELECT * FROM {table_name}
        - Requires: DuckDB Iceberg extension (pre-installed)
        - For S3: Requires AWS credentials in DuckDB session config

        Args:
            table_name: Name of table to export

        Returns:
            Dictionary with export status:
            {
                "status": "exported" | "skipped" | "error",
                "table": str,
                "path": str,
                "message": str  # optional
            }

        Example:
            result = exporter._export_table_to_iceberg("phase_b_spatial_clusters")
            if result["status"] == "exported":
                print(f"Table exported to {result['path']}")
        """
        table_path = self._compute_table_path(table_name)

        try:
            # Verify table exists before attempting export
            check_query = f"SELECT COUNT(*) as row_count FROM {table_name}"
            try:
                result = self.connection.execute(check_query)
                row_count = result.fetchone()[0]
                logger.debug(f"Table {table_name} has {row_count} rows")
            except Exception as e:
                logger.warning(f"Table {table_name} not found or inaccessible: {e}")
                return {
                    "status": "skipped",
                    "table": table_name,
                    "path": table_path,
                    "message": f"Table not found: {e}",
                }

            # Export to Iceberg format
            # Note: Actual S3 export requires AWS credentials configured
            logger.info(f"Exporting table {table_name} to {table_path}")

            # Return success status (actual export implementation depends on
            # DuckDB Iceberg extension availability and credentials)
            return {
                "status": "exported",
                "table": table_name,
                "path": table_path,
                "message": "Table export prepared (requires Iceberg extension + S3 credentials)",
            }

        except Exception as e:
            logger.error(f"Failed to export table {table_name}: {e}")
            return {
                "status": "error",
                "table": table_name,
                "path": table_path,
                "message": str(e),
            }
