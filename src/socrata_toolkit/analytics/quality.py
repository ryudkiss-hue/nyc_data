"""
Data Quality and Integrity skills for the SIM Mission Control workstation.
Implements DataQualityAudit, SchemaMapper, and MetricReconciliation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from socrata_toolkit.analytics import AnalysisResult, BaseSkill
from socrata_toolkit.quality.profiler import ProfileGenerator

logger = logging.getLogger(__name__)


class DataQualityAudit(BaseSkill):
    """
    Performs comprehensive data quality assessment.

    Includes:
    - The Four Moments (Mean, Variance, Skewness, Kurtosis)
    - Null count tracking
    - Outlier detection (Z-score threshold > 3)
    """

    def run(self, df: pd.DataFrame, table_name: str = "dataset", **kwargs) -> AnalysisResult:
        """
        Executes the audit on a DataFrame.

        Args:
            df (pd.DataFrame): The dataset to audit.
            table_name (str): Identifier for the table.

        Returns:
            AnalysisResult: Detailed quality metrics.
        """
        self.logger.info("Starting DataQualityAudit for %s", table_name)

        try:
            # 1. Basic Profiling
            generator = ProfileGenerator()
            profile = generator.profile_dataset(df, table_name)

            # 2. The Four Moments (Mandatory per GEMINI.md)
            moments: dict[str, dict[str, float]] = {}
            numeric_cols = df.select_dtypes(include=[np.number]).columns

            for col in numeric_cols:
                clean_series = df[col].dropna()
                if len(clean_series) < 2:
                    continue

                moments[col] = {
                    "mean": float(clean_series.mean()),
                    "variance": float(clean_series.var()),
                    "skewness": float(stats.skew(clean_series)),
                    "kurtosis": float(stats.kurtosis(clean_series)),
                }

            # 3. Outlier Detection
            outliers: dict[str, list[float]] = {}
            for col in numeric_cols:
                clean_series = df[col].dropna()
                if len(clean_series) < 2:
                    continue

                z_scores = np.abs(stats.zscore(clean_series))
                outlier_mask = z_scores > 3
                if outlier_mask.any():
                    outliers[col] = clean_series[outlier_mask].tolist()

            # 4. Null Counts
            null_counts = df.isnull().sum().to_dict()

            result_data = {
                "table_profile": profile.to_dict(),
                "four_moments": moments,
                "outliers": outliers,
                "null_counts": null_counts,
                "row_count": len(df),
            }

            self.logger.info(
                "Completed DataQualityAudit for %s. Found %d numeric columns and %d outlier groups.",
                table_name,
                len(moments),
                len(outliers),
            )

            return AnalysisResult(
                skill_name="DataQualityAudit",
                success=True,
                data=result_data,
                metadata={"table_name": table_name},
            )

        except Exception as e:
            self.logger.error(
                "DataQualityAudit failed for %s: %s", table_name, str(e), exc_info=True
            )
            return AnalysisResult(
                skill_name="DataQualityAudit",
                success=False,
                data={"error": str(e)},
                metadata={"table_name": table_name},
            )


class SchemaMapper(BaseSkill):
    """
    Maps DuckDB schema characteristics to Socrata metadata definitions.

    Identifies:
    - Missing columns (in Socrata but not DuckDB)
    - New columns (in DuckDB but not Socrata - schema evolution)
    - Type alignment (future implementation)
    """

    def run(self, dataset_key: str, **kwargs) -> AnalysisResult:
        """
        Args:
            dataset_key (str): The key from datasets.yaml to map.
        """
        self.logger.info("Starting SchemaMapper for %s", dataset_key)

        try:
            # 1. Load Expected Schema from Registry
            repo_root = Path(__file__).resolve().parents[3]
            config_path = repo_root / "config" / "datasets.yaml"

            if not config_path.exists():
                return AnalysisResult("SchemaMapper", False, {"error": "datasets.yaml not found"})

            import yaml

            with open(config_path) as f:
                registry = yaml.safe_load(f)

            if dataset_key not in registry.get("datasets", {}):
                return AnalysisResult(
                    "SchemaMapper", False, {"error": f"Dataset '{dataset_key}' not in registry"}
                )

            expected_cols = set(registry["datasets"][dataset_key].get("columns", []))

            # 2. Get Actual Schema from DuckDB
            from socrata_toolkit.core.duckdb_store import DuckDBManager

            manager = DuckDBManager()

            # Check if table exists
            tables = manager.conn.execute("SHOW TABLES").fetchall()
            if not any(t[0] == dataset_key for t in tables):
                return AnalysisResult(
                    "SchemaMapper", False, {"error": f"Table '{dataset_key}' not found in DuckDB"}
                )

            actual_info = manager.conn.execute(f'PRAGMA table_info("{dataset_key}")').fetchall()
            actual_cols = {row[1] for row in actual_info}

            # 3. Compare
            missing = list(expected_cols - actual_cols)
            extra = list(actual_cols - expected_cols)

            result_data = {
                "dataset_key": dataset_key,
                "expected_count": len(expected_cols),
                "actual_count": len(actual_cols),
                "missing_columns": missing,
                "extra_columns": extra,
                "is_aligned": len(missing) == 0 and len(extra) == 0,
            }

            self.logger.info(
                "SchemaMapper for %s complete. Aligned: %s", dataset_key, result_data["is_aligned"]
            )
            if extra:
                self.logger.warning("Detected %d drifted columns in %s", len(extra), dataset_key)

            return AnalysisResult(
                skill_name="SchemaMapper",
                success=True,
                data=result_data,
                metadata={"dataset_key": dataset_key},
            )

        except Exception as e:
            self.logger.error("SchemaMapper failed for %s: %s", dataset_key, str(e), exc_info=True)
            return AnalysisResult("SchemaMapper", False, {"error": str(e)})


class MetricReconciliation(BaseSkill):
    """
    Investigates and resolves metric discrepancies across data sources.

    Currently reconciles row counts between DuckDB and Socrata Registry metadata.
    """

    def run(self, dataset_key: str, **kwargs) -> AnalysisResult:
        self.logger.info("Starting MetricReconciliation for %s", dataset_key)

        try:
            # 1. Get DuckDB Count
            from socrata_toolkit.core.duckdb_store import DuckDBManager, DuckDBRepository

            manager = DuckDBManager()
            repo = DuckDBRepository(manager, dataset_key)
            local_count = repo.count()

            # 2. Get Registry Metadata (Simulated Source Count)
            repo_root = Path(__file__).resolve().parents[3]
            config_path = repo_root / "config" / "datasets.yaml"

            import yaml

            with open(config_path) as f:
                registry = yaml.safe_load(f)

            registry_entry = registry.get("datasets", {}).get(dataset_key, {})
            # Registry might have a cached count or we can use the 'last_updated' as proxy for checking drift
            # For reconciliation, we typically want the live SODA3 count vs local

            # For this 'hardcoded' version, we report the local vs whatever is in datasets.yaml
            expected_count = registry_entry.get("row_count", "Unknown")

            delta = 0
            if isinstance(expected_count, int):
                delta = local_count - expected_count

            result_data = {
                "dataset_key": dataset_key,
                "local_count": local_count,
                "registry_count": expected_count,
                "delta": delta,
                "reconciled": delta == 0 if isinstance(expected_count, int) else "N/A",
            }

            self.logger.info(
                "MetricReconciliation for %s complete. Local: %d, Registry: %s",
                dataset_key,
                local_count,
                expected_count,
            )

            return AnalysisResult(
                skill_name="MetricReconciliation",
                success=True,
                data=result_data,
                metadata={"dataset_key": dataset_key},
            )

        except Exception as e:
            self.logger.error("MetricReconciliation failed for %s: %s", dataset_key, str(e))
            err_msg = str(e)
            # Normalize DuckDB "does not exist" catalog errors to "not found"
            if "does not exist" in err_msg.lower():
                err_msg = f"Table not found: {err_msg}"
            return AnalysisResult("MetricReconciliation", False, {"error": err_msg})
