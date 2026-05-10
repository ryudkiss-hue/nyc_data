"""
Data Quality Profiler - Statistical Analysis and Profile Generation

Analyzes datasets to generate column-level and table-level statistics, detect outliers,
identify patterns, and suggest data quality expectations. Tracks data drift over time
by comparing profiles.

Standards: Python 3.9+, full type hints, comprehensive docstrings, logging
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class DataType(Enum):
    """Detected data types for columns."""
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    STRING = "string"
    UNKNOWN = "unknown"


@dataclass
class ColumnProfile:
    """Statistics for a single column.
    
    Attributes:
        column_name: Name of the column
        data_type: Detected data type
        count: Total non-null count
        null_count: Number of NULL values
        null_percentage: Percentage of NULLs (0-100)
        cardinality: Number of unique values
        cardinality_ratio: Unique / total (0-1)
        min_value: Minimum value (numeric/string length)
        max_value: Maximum value (numeric/string length)
        mean: Mean value (numeric only)
        median: Median value (numeric only)
        std_dev: Standard deviation (numeric only)
        skewness: Distribution skewness (numeric only)
        kurtosis: Distribution kurtosis (numeric only)
        outlier_count: Number of outliers detected (IQR method)
        most_common_values: Top N most frequent values
        value_range: Min-max range for numeric columns
        pattern_matches: Regex patterns detected
        entropy: Shannon entropy for categorical data
    """
    column_name: str
    data_type: DataType
    count: int
    null_count: int
    null_percentage: float
    cardinality: int
    cardinality_ratio: float
    min_value: Optional[float | str] = None
    max_value: Optional[float | str] = None
    mean: Optional[float] = None
    median: Optional[float] = None
    std_dev: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    outlier_count: int = 0
    most_common_values: Dict[Any, int] = field(default_factory=dict)
    value_range: Optional[Tuple[float, float]] = None
    pattern_matches: Dict[str, int] = field(default_factory=dict)
    entropy: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "column_name": self.column_name,
            "data_type": self.data_type.value,
            "count": self.count,
            "null_count": self.null_count,
            "null_percentage": self.null_percentage,
            "cardinality": self.cardinality,
            "cardinality_ratio": self.cardinality_ratio,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "mean": self.mean,
            "median": self.median,
            "std_dev": self.std_dev,
            "skewness": self.skewness,
            "kurtosis": self.kurtosis,
            "outlier_count": self.outlier_count,
            "most_common_values": dict(self.most_common_values),
            "value_range": self.value_range,
            "pattern_matches": dict(self.pattern_matches),
            "entropy": self.entropy,
        }


@dataclass
class TableProfile:
    """Statistics for an entire table/dataset.
    
    Attributes:
        table_name: Name of the table
        row_count: Total number of rows
        column_count: Total number of columns
        column_profiles: Dict mapping column name to ColumnProfile
        created_at: When the profile was generated
        version: Profile version for tracking changes
    """
    table_name: str
    row_count: int
    column_count: int
    column_profiles: Dict[str, ColumnProfile]
    created_at: datetime
    version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "table_name": self.table_name,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "created_at": self.created_at.isoformat(),
            "version": self.version,
            "column_profiles": {
                name: prof.to_dict() for name, prof in self.column_profiles.items()
            },
        }

    def to_json(self, path: Path | str) -> None:
        """Save profile to JSON file.
        
        Args:
            path: File path to save to
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        logger.info(f"Saved profile for {self.table_name} to {path}")

    @classmethod
    def from_json(cls, path: Path | str) -> TableProfile:
        """Load profile from JSON file.
        
        Args:
            path: File path to load from
            
        Returns:
            Loaded TableProfile
        """
        path = Path(path)
        with open(path) as f:
            data = json.load(f)

        column_profiles = {}
        for col_name, col_data in data["column_profiles"].items():
            col_data["data_type"] = DataType(col_data["data_type"])
            column_profiles[col_name] = ColumnProfile(**col_data)

        return cls(
            table_name=data["table_name"],
            row_count=data["row_count"],
            column_count=data["column_count"],
            column_profiles=column_profiles,
            created_at=datetime.fromisoformat(data["created_at"]),
            version=data.get("version", "1.0.0"),
        )


@dataclass
class DriftReport:
    """Report of changes between two profiles (schema/data drift).
    
    Attributes:
        table_name: Name of the table
        compared_at: When comparison was performed
        changes: List of detected changes
        severity_level: Overall severity (CRITICAL, HIGH, MEDIUM, LOW)
    """
    table_name: str
    compared_at: datetime
    changes: List[Dict[str, Any]] = field(default_factory=list)
    severity_level: str = "LOW"

    def add_change(
        self,
        change_type: str,
        column: str,
        old_value: Any,
        new_value: Any,
        severity: str = "MEDIUM",
    ) -> None:
        """Add a detected change to the report.
        
        Args:
            change_type: Type of change (e.g., 'cardinality_increased')
            column: Column affected
            old_value: Previous value
            new_value: Current value
            severity: Severity level
        """
        self.changes.append({
            "change_type": change_type,
            "column": column,
            "old_value": old_value,
            "new_value": new_value,
            "severity": severity,
        })

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "table_name": self.table_name,
            "compared_at": self.compared_at.isoformat(),
            "change_count": len(self.changes),
            "severity_level": self.severity_level,
            "changes": self.changes,
        }


class ProfileGenerator:
    """Generates data quality profiles for datasets.
    
    Analyzes datasets to extract statistics, detect anomalies, identify patterns,
    and generate expectations. Supports large datasets with efficient computation.
    """

    def __init__(self, sample_size: int = 10000):
        """Initialize profiler.
        
        Args:
            sample_size: Maximum rows to analyze for patterns (for large datasets)
        """
        self.sample_size = sample_size

    def profile_dataset(self, df: pd.DataFrame, table_name: str = "unknown") -> TableProfile:
        """Generate a profile for a dataset.
        
        Args:
            df: DataFrame to profile
            table_name: Name of the table
            
        Returns:
            TableProfile with statistics for all columns
        """
        logger.info(f"Profiling dataset {table_name} with {len(df)} rows")

        column_profiles = {}
        for column in df.columns:
            col_profile = self._profile_column(df[column], column)
            column_profiles[column] = col_profile

        profile = TableProfile(
            table_name=table_name,
            row_count=len(df),
            column_count=len(df.columns),
            column_profiles=column_profiles,
            created_at=datetime.utcnow(),
        )

        logger.info(
            f"Completed profiling: {len(df)} rows, {len(df.columns)} columns, "
            f"{sum(1 for p in column_profiles.values() if p.null_count > 0)} with nulls"
        )
        return profile

    def _profile_column(self, series: pd.Series, column_name: str) -> ColumnProfile:
        """Profile a single column.
        
        Args:
            series: Series to profile
            column_name: Column name
            
        Returns:
            ColumnProfile with statistics
        """
        # Basic statistics
        count = series.count()
        null_count = series.isna().sum()
        null_percentage = (null_count / len(series) * 100) if len(series) > 0 else 0
        cardinality = series.nunique()
        cardinality_ratio = cardinality / count if count > 0 else 0

        # Detect data type
        data_type = self._detect_data_type(series)

        # Type-specific statistics
        if data_type == DataType.NUMERIC:
            numeric_stats = self._analyze_numeric(series)
        else:
            numeric_stats = {}

        if data_type in (DataType.CATEGORICAL, DataType.STRING):
            categorical_stats = self._analyze_categorical(series)
        else:
            categorical_stats = {}

        # Common statistics
        most_common = series.value_counts().head(10).to_dict() if count > 0 else {}

        profile = ColumnProfile(
            column_name=column_name,
            data_type=data_type,
            count=int(count),
            null_count=int(null_count),
            null_percentage=round(null_percentage, 2),
            cardinality=int(cardinality),
            cardinality_ratio=round(cardinality_ratio, 4),
            most_common_values=most_common,
            **numeric_stats,
            **categorical_stats,
        )

        return profile

    def _detect_data_type(self, series: pd.Series) -> DataType:
        """Detect the data type of a series.
        
        Args:
            series: Series to analyze
            
        Returns:
            Detected DataType
        """
        # Use pandas dtype inference
        if pd.api.types.is_numeric_dtype(series):
            return DataType.NUMERIC
        elif pd.api.types.is_bool_dtype(series):
            return DataType.BOOLEAN
        elif pd.api.types.is_datetime64_any_dtype(series):
            return DataType.DATETIME
        else:
            return DataType.STRING

    def _analyze_numeric(self, series: pd.Series) -> Dict[str, Any]:
        """Analyze numeric column.
        
        Args:
            series: Numeric series
            
        Returns:
            Dictionary with numeric statistics
        """
        numeric_data = pd.to_numeric(series, errors="coerce")
        if not isinstance(numeric_data, pd.Series):
            return {}
        numeric_series = numeric_data.dropna()

        if len(numeric_series) == 0:
            return {}

        # Calculate statistics
        min_val = numeric_series.min()
        max_val = numeric_series.max()
        mean_val = numeric_series.mean()
        median_val = numeric_series.median()
        std_val = numeric_series.std()
        skew_val = numeric_series.skew()
        kurt_val = numeric_series.kurtosis()

        # Detect outliers using IQR method
        q1 = numeric_series.quantile(0.25)
        q3 = numeric_series.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outlier_count = ((numeric_series < lower_bound) | (numeric_series > upper_bound)).sum()

        # Safely convert values, handling NaN and complex numbers
        skew_result = None
        if pd.notna(skew_val):
            try:
                skew_result = float(skew_val)
            except (TypeError, ValueError):
                skew_result = None

        kurt_result = None
        if pd.notna(kurt_val):
            try:
                kurt_result = float(kurt_val)
            except (TypeError, ValueError):
                kurt_result = None

        return {
            "min_value": float(min_val) if pd.notna(min_val) else None,
            "max_value": float(max_val) if pd.notna(max_val) else None,
            "mean": float(mean_val) if pd.notna(mean_val) else None,
            "median": float(median_val) if pd.notna(median_val) else None,
            "std_dev": float(std_val) if pd.notna(std_val) else None,
            "skewness": skew_result,
            "kurtosis": kurt_result,
            "outlier_count": int(outlier_count),
            "value_range": (float(min_val), float(max_val)) if pd.notna(min_val) else None,
        }

    def _analyze_categorical(self, series: pd.Series) -> Dict[str, Any]:
        """Analyze categorical/string column.
        
        Args:
            series: String series
            
        Returns:
            Dictionary with categorical statistics
        """
        # Calculate entropy
        value_counts = series.value_counts()
        total = value_counts.sum()
        probabilities = value_counts / total
        entropy = -(probabilities * np.log2(probabilities + 1e-10)).sum()

        # String length analysis for string columns
        stats: Dict[str, Any] = {"entropy": float(entropy)}

        if series.dtype == "object":
            str_lengths = series.astype(str).str.len()
            stats["min_value"] = int(str_lengths.min())
            stats["max_value"] = int(str_lengths.max())

        return stats

    def suggest_expectations(self, profile: TableProfile) -> List[Dict[str, Any]]:
        """Suggest data quality expectations based on a profile.
        
        Args:
            profile: TableProfile to analyze
            
        Returns:
            List of suggested expectations
        """
        suggestions = []

        for col_name, col_profile in profile.column_profiles.items():
            # Suggest column existence
            suggestions.append({
                "expectation_type": "column_exists",
                "kwargs": {"column": col_name},
                "severity": "critical",
                "rationale": f"Column {col_name} is present in the data",
            })

            # Suggest not-null for mostly non-null columns
            if col_profile.null_percentage < 5:
                mostly_val = max(0.95, 1 - (col_profile.null_percentage / 100))
                suggestions.append({
                    "expectation_type": "column_values_to_not_be_null",
                    "kwargs": {"column": col_name, "mostly": mostly_val},
                    "severity": "high",
                    "rationale": f"Column {col_name} is {100 - col_profile.null_percentage:.1f}% non-null",
                })

            # Suggest value ranges for numeric columns
            if col_profile.data_type == DataType.NUMERIC and col_profile.value_range:
                min_val, max_val = col_profile.value_range
                suggestions.append({
                    "expectation_type": "column_values_to_be_between",
                    "kwargs": {
                        "column": col_name,
                        "min_value": float(min_val),
                        "max_value": float(max_val),
                    },
                    "severity": "medium",
                    "rationale": f"Column {col_name} values range from {min_val:.2f} to {max_val:.2f}",
                })

            # Suggest cardinality limits for high-cardinality columns
            if col_profile.cardinality > 100:
                suggestions.append({
                    "expectation_type": "column_cardinality_limit",
                    "kwargs": {"column": col_name, "max_cardinality": col_profile.cardinality},
                    "severity": "low",
                    "rationale": f"Column {col_name} has {col_profile.cardinality} unique values",
                })

        return suggestions

    def compare_profiles(
        self,
        profile_old: TableProfile,
        profile_new: TableProfile,
        threshold_cardinality: float = 0.2,
        threshold_null: float = 0.1,
    ) -> DriftReport:
        """Compare two profiles to detect data drift.
        
        Args:
            profile_old: Previous profile
            profile_new: Current profile
            threshold_cardinality: Threshold for cardinality change (0-1)
            threshold_null: Threshold for null percentage change (0-1)
            
        Returns:
            DriftReport with detected changes
        """
        report = DriftReport(
            table_name=profile_old.table_name,
            compared_at=datetime.utcnow(),
        )

        # Check row count changes
        row_change_pct = abs(profile_new.row_count - profile_old.row_count) / max(
            profile_old.row_count, 1
        )
        if row_change_pct > 0.5:
            report.add_change(
                "row_count_changed",
                "table",
                profile_old.row_count,
                profile_new.row_count,
                "high" if row_change_pct > 1.0 else "medium",
            )

        # Check for missing columns
        old_cols = set(profile_old.column_profiles.keys())
        new_cols = set(profile_new.column_profiles.keys())

        missing_cols = old_cols - new_cols
        for col in missing_cols:
            report.add_change(
                "column_removed",
                col,
                "present",
                "missing",
                "critical",
            )

        new_cols_added = new_cols - old_cols
        for col in new_cols_added:
            report.add_change(
                "column_added",
                col,
                "missing",
                "present",
                "low",
            )

        # Check for column-level drift
        for col_name in old_cols & new_cols:
            old_col = profile_old.column_profiles[col_name]
            new_col = profile_new.column_profiles[col_name]

            # Cardinality drift
            card_change = abs(new_col.cardinality - old_col.cardinality) / max(
                old_col.cardinality, 1
            )
            if card_change > threshold_cardinality:
                report.add_change(
                    "cardinality_changed",
                    col_name,
                    old_col.cardinality,
                    new_col.cardinality,
                    "medium",
                )

            # Null percentage drift
            null_change = abs(new_col.null_percentage - old_col.null_percentage)
            if null_change > threshold_null * 100:
                report.add_change(
                    "null_percentage_changed",
                    col_name,
                    old_col.null_percentage,
                    new_col.null_percentage,
                    "high",
                )

            # Data type change
            if old_col.data_type != new_col.data_type:
                report.add_change(
                    "data_type_changed",
                    col_name,
                    old_col.data_type.value,
                    new_col.data_type.value,
                    "critical",
                )

        # Determine overall severity
        critical_changes = sum(1 for c in report.changes if c["severity"] == "critical")
        high_changes = sum(1 for c in report.changes if c["severity"] == "high")

        if critical_changes > 0:
            report.severity_level = "CRITICAL"
        elif high_changes > 0:
            report.severity_level = "HIGH"
        elif len(report.changes) > 0:
            report.severity_level = "MEDIUM"
        else:
            report.severity_level = "LOW"

        logger.info(
            f"Drift analysis completed: {len(report.changes)} changes detected, "
            f"severity={report.severity_level}"
        )

        return report

    def detect_schema_drift(
        self, profile_old: TableProfile, profile_new: TableProfile
    ) -> Dict[str, Any]:
        """Detect structural schema changes between profiles.
        
        Args:
            profile_old: Previous profile
            profile_new: Current profile
            
        Returns:
            Dictionary with schema changes
        """
        drift_report = self.compare_profiles(profile_old, profile_new)

        schema_changes = {
            "columns_added": [],
            "columns_removed": [],
            "type_changes": [],
            "nullability_changes": [],
        }

        for change in drift_report.changes:
            if change["change_type"] == "column_added":
                schema_changes["columns_added"].append(change["column"])
            elif change["change_type"] == "column_removed":
                schema_changes["columns_removed"].append(change["column"])
            elif change["change_type"] == "data_type_changed":
                schema_changes["type_changes"].append(
                    {
                        "column": change["column"],
                        "old_type": change["old_value"],
                        "new_type": change["new_value"],
                    }
                )

        return schema_changes

    def generate_summary(self, profile: TableProfile) -> Dict[str, Any]:
        """Generate a summary of profile statistics.
        
        Args:
            profile: TableProfile to summarize
            
        Returns:
            Dictionary with summary statistics
        """
        cols_with_nulls = sum(
            1 for p in profile.column_profiles.values() if p.null_count > 0
        )
        high_cardinality_cols = sum(
            1
            for p in profile.column_profiles.values()
            if p.cardinality_ratio > 0.9
        )
        numeric_cols = sum(
            1
            for p in profile.column_profiles.values()
            if p.data_type == DataType.NUMERIC
        )

        return {
            "table_name": profile.table_name,
            "row_count": profile.row_count,
            "column_count": profile.column_count,
            "columns_with_nulls": cols_with_nulls,
            "high_cardinality_columns": high_cardinality_cols,
            "numeric_columns": numeric_cols,
            "profile_generated_at": profile.created_at.isoformat(),
        }
