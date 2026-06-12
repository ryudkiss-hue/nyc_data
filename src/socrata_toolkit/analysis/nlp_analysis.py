"""
Integration layer: Fetch data + classify + generate insights.

Combines NLP classification with hardcoded analysis to reduce LLM token usage.
"""

import logging
from typing import Optional

import pandas as pd

from .nlp_classifier import ClassificationResult, TextClassifierPipeline

logger = logging.getLogger(__name__)

class DatasetAnalyzerWithNLP:
    """Fetch, classify, and analyze any dataset from the NYC DOT registry."""

    # Maps dataset keys to expected text columns and classifier type
    DATASET_CONFIG = {
        # Inspection data
        "inspection": {
            "text_column": "description",
            "classifier_type": "violations",
        },
        "violations": {
            "text_column": "description",
            "classifier_type": "violations",
        },
        "dismissals": {
            "text_column": "reason",
            "classifier_type": "violations",
        },
        "correspondences": {
            "text_column": "comment",
            "classifier_type": "violations",
        },
        "curb_metal_protruding": {
            "text_column": "description",
            "classifier_type": "violations",
        },

        # Complaints
        "complaints_311": {
            "text_column": "description",
            "classifier_type": "complaints",
        },
        "ramp_complaints": {
            "text_column": "description",
            "classifier_type": "complaints",
        },

        # Tree data
        "tree_damage": {
            "text_column": "description",
            "classifier_type": "tree_damage",
        },

        # Construction
        "street_construction_inspections": {
            "text_column": "finding_description",
            "classifier_type": "construction",
        },
        "street_closures_block": {
            "text_column": "description",
            "classifier_type": "construction",
        },
        "street_permits": {
            "text_column": "work_description",
            "classifier_type": "construction",
        },
    }

    def __init__(self):
        """Initialize classifier pipeline."""
        self.classifier_pipeline = TextClassifierPipeline()

    def analyze_dataset(
        self,
        df: pd.DataFrame,
        dataset_key: str,
        text_column: Optional[str] = None,
    ) -> dict:
        """
        Classify and analyze a dataset.

        Args:
            df: Dataframe with text to classify
            dataset_key: Key from registry (e.g., 'violations', 'complaints_311')
            text_column: Override default text column name

        Returns:
            Dict with enriched dataframe and summary statistics
        """
        config = self.DATASET_CONFIG.get(dataset_key)
        if not config:
            logger.warning(f"Dataset '{dataset_key}' not configured. Skipping classification.")
            return {"dataframe": df, "summary": None, "error": "Unknown dataset"}

        # Use provided column or default from config
        col = text_column or config["text_column"]

        if col not in df.columns:
            logger.warning(f"Column '{col}' not found in dataframe")
            return {"dataframe": df, "summary": None, "error": f"Column '{col}' not found"}

        # Classify
        logger.info(f"Classifying {len(df)} records from '{dataset_key}' using {col}")
        enriched_df = self.classifier_pipeline.classify_dataset(df, dataset_key, col)

        # Summarize based on classifier type
        classifier_type = config["classifier_type"]
        if classifier_type == "violations":
            summary = self._summarize_violations(enriched_df)
        elif classifier_type == "complaints":
            summary = self._summarize_complaints(enriched_df)
        elif classifier_type == "tree_damage":
            summary = self._summarize_tree_damage(enriched_df)
        elif classifier_type == "construction":
            summary = self._summarize_construction(enriched_df)
        else:
            summary = None

        return {
            "dataframe": enriched_df,
            "summary": summary,
            "dataset_key": dataset_key,
            "total_records": len(enriched_df),
            "classifier_type": classifier_type,
        }

    def _summarize_violations(self, df: pd.DataFrame) -> pd.DataFrame:
        """Summarize violation classifications."""
        if "violation_type" not in df.columns:
            return None

        summary = (
            df.groupby("violation_type")
            .agg({
                "violation_severity": ["count", "mean", "max"],
                "violation_confidence": "mean",
            })
            .round(2)
        )
        summary.columns = ["count", "avg_severity", "max_severity", "avg_confidence"]
        return summary.sort_values("count", ascending=False)

    def _summarize_complaints(self, df: pd.DataFrame) -> pd.DataFrame:
        """Summarize complaint classifications."""
        if "complaint_category" not in df.columns:
            return None

        summary = (
            df.groupby("complaint_category")
            .agg({
                "complaint_urgency": ["count", "mean", "max"],
                "complaint_confidence": "mean",
            })
            .round(2)
        )
        summary.columns = ["count", "avg_urgency", "max_urgency", "avg_confidence"]
        return summary.sort_values("count", ascending=False)

    def _summarize_tree_damage(self, df: pd.DataFrame) -> pd.DataFrame:
        """Summarize tree damage classifications."""
        if "damage_type" not in df.columns:
            return None

        summary = (
            df.groupby("damage_type")
            .agg({
                "damage_severity": ["count", "mean", "max"],
                "damage_confidence": "mean",
            })
            .round(2)
        )
        summary.columns = ["count", "avg_severity", "max_severity", "avg_confidence"]
        return summary.sort_values("count", ascending=False)

    def _summarize_construction(self, df: pd.DataFrame) -> pd.DataFrame:
        """Summarize construction finding classifications."""
        if "finding_type" not in df.columns:
            return None

        summary = (
            df.groupby("finding_type")
            .agg({
                "finding_severity": ["count", "mean", "max"],
                "finding_confidence": "mean",
            })
            .round(2)
        )
        summary.columns = ["count", "avg_severity", "max_severity", "avg_confidence"]
        return summary.sort_values("count", ascending=False)

    def get_high_severity_records(
        self, df: pd.DataFrame, dataset_key: str, severity_threshold: float = 70
    ) -> pd.DataFrame:
        """
        Extract high-severity records for follow-up analysis.

        Args:
            df: Enriched dataframe from analyze_dataset
            dataset_key: Dataset type
            severity_threshold: Minimum severity to include

        Returns:
            Filtered dataframe with high-severity records
        """
        classifier_type = self.DATASET_CONFIG.get(dataset_key, {}).get("classifier_type")

        if classifier_type == "violations":
            severity_col = "violation_severity"
        elif classifier_type == "complaints":
            severity_col = "complaint_urgency"
        elif classifier_type == "tree_damage":
            severity_col = "damage_severity"
        elif classifier_type == "construction":
            severity_col = "finding_severity"
        else:
            return pd.DataFrame()

        if severity_col not in df.columns:
            return pd.DataFrame()

        return df[df[severity_col] >= severity_threshold].sort_values(
            severity_col, ascending=False
        )

    def borough_breakdown(
        self, df: pd.DataFrame, dataset_key: str, borough_column: str = "borough"
    ) -> dict[str, pd.DataFrame]:
        """
        Break down classifications by borough.

        Args:
            df: Enriched dataframe
            dataset_key: Dataset type
            borough_column: Name of borough column

        Returns:
            Dict mapping borough to summary stats
        """
        if borough_column not in df.columns:
            logger.warning(f"Borough column '{borough_column}' not found")
            return {}

        classifier_type = self.DATASET_CONFIG.get(dataset_key, {}).get("classifier_type")

        if classifier_type == "violations":
            category_col = "violation_type"
            severity_col = "violation_severity"
        elif classifier_type == "complaints":
            category_col = "complaint_category"
            severity_col = "complaint_urgency"
        elif classifier_type == "tree_damage":
            category_col = "damage_type"
            severity_col = "damage_severity"
        elif classifier_type == "construction":
            category_col = "finding_type"
            severity_col = "finding_severity"
        else:
            return {}

        borough_breakdowns = {}
        for borough in df[borough_column].unique():
            borough_df = df[df[borough_column] == borough]
            borough_breakdowns[borough] = (
                borough_df.groupby(category_col)
                .agg({
                    severity_col: ["count", "mean"],
                })
                .round(2)
            )

        return borough_breakdowns
