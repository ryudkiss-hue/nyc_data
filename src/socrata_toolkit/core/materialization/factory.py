"""Generalized materialization factory orchestrator."""
import json
import logging
from pathlib import Path
from typing import Dict, Optional

import duckdb

from .builders import *  # noqa: F401,F403 (auto-register builders)
from .lineage import MartLineage
from .quality import MartQuality
from .registry import BuilderRegistry

logger = logging.getLogger(__name__)


class MaterializationFactory:
    """Orchestrates materialization of all mats from config.

    Supports multiple config types (analytics, validation, monitoring, etc.)
    and dynamically discovers builders from registry.
    """

    def __init__(self, dataset_configs: dict, conn: duckdb.DuckDBPyConnection = None):
        """Initialize factory.

        Args:
            dataset_configs: All dataset configurations from dataset_config.json
            conn: DuckDB connection (if None, uses default)
        """
        self.dataset_configs = dataset_configs
        self.conn = conn
        self.lineage = MartLineage()
        self.quality = MartQuality()

    def materialize(self, mat_config: dict, schema: str = "analytics") -> Dict[str, dict]:
        """Materialize all mats from config.

        Args:
            mat_config: Mart definitions (from analytics_config.json or similar)
            schema: Target schema (analytics, validation, monitoring, etc.)

        Returns:
            Dict of status dicts: {mat_name: {status, table, row_count, ...}}
        """
        results = {}

        # Iterate through all sections in config
        for section_key in mat_config:
            if section_key in ["metadata"]:
                continue  # Skip metadata

            section_mats = mat_config[section_key]
            if not isinstance(section_mats, list):
                continue

            for mat_def in section_mats:
                mat_name = mat_def.get("name")
                if not mat_name:
                    logger.warning(f"Mart definition missing 'name': {mat_def}")
                    continue

                try:
                    # Get builder from registry
                    builder_type = mat_def.get("builder")
                    if not builder_type:
                        logger.error(f"Mart {mat_name} missing 'builder' field")
                        results[mat_name] = {
                            "status": "error",
                            "error": "Missing 'builder' field",
                            "table": f"{schema}.{mat_name}",
                        }
                        continue

                    builder_class = BuilderRegistry.get(builder_type)

                    # Instantiate builder
                    builder = builder_class(mat_def, self.dataset_configs, self.conn)

                    # Materialize
                    result = builder.materialize(schema)

                    # Track lineage
                    if result["status"] == "success":
                        datasets = mat_def.get("datasets", [])
                        self.lineage.record(
                            mart_name=mat_name,
                            source_datasets=datasets,
                            target_schema=schema,
                            target_table=f"{schema}.{mat_name}",
                            row_count=result["row_count"],
                            conn=self.conn,
                        )

                        # Track quality
                        self.quality.track_metrics(
                            mart_name=mat_name,
                            row_count=result["row_count"],
                            schema={},  # TODO: extract actual schema from table
                            materialized_at="NOW()",
                            conn=self.conn,
                        )

                    results[mat_name] = result

                except Exception as e:
                    logger.error(f"Failed to materialize {mat_name}: {e}")
                    results[mat_name] = {
                        "status": "error",
                        "error": str(e),
                        "table": f"{schema}.{mat_name}",
                    }

        return results

    @staticmethod
    def from_config_files(
        dataset_config_path: str,
        mat_config_path: str,
        conn: duckdb.DuckDBPyConnection = None,
    ):
        """Create factory from config files.

        Args:
            dataset_config_path: Path to dataset_config.json
            mat_config_path: Path to analytics_config.json (or equivalent)
            conn: DuckDB connection

        Returns:
            Materialized results
        """
        # Load configs
        with open(dataset_config_path) as f:
            dataset_configs = json.load(f)

        with open(mat_config_path) as f:
            mat_config = json.load(f)

        # Determine schema from config path
        schema = "analytics"
        if "validation" in mat_config_path:
            schema = "validation"
        elif "monitoring" in mat_config_path:
            schema = "monitoring"

        # Create factory and materialize
        factory = MaterializationFactory(dataset_configs, conn)
        return factory.materialize(mat_config, schema=schema)
