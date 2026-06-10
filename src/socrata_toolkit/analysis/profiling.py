from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd

from ..core import DTYPE_NUM

logger = logging.getLogger(__name__)

@dataclass
class DataProfile:
    """Comprehensive profile of a DataFrame conforming to the Four Moments of characterization."""
    row_count: int
    column_count: int
    columns: list[dict[str, Any]]
    null_counts: dict[str, int]
    quality_score: int
    warnings: list[str]
    numeric_summary: dict[str, Any]
    moments: dict[str, dict[str, float]] = __import__("dataclasses").field(default_factory=dict)  # Map of column -> {mean, var, skew, kurt}

def profile_dataframe(df: pd.DataFrame) -> DataProfile:
    """Produce a comprehensive profile characterization of the dataframe."""
    if df.empty:
        return DataProfile(0, 0, [], {}, 0, ["Input DataFrame is empty"], {}, {})

    row_count = len(df)
    null_counts_series = df.isna().sum()
    null_pcts = (null_counts_series / max(row_count, 1)) * 100
    unique_counts = df.nunique()
    dtypes = df.dtypes.astype(str)

    cols = []
    warnings = []
    moments = {}

    numeric_df = df.select_dtypes(include=DTYPE_NUM)
    for col in df.columns:
        col_str = str(col)
        null_pct = round(float(null_pcts[col]), 2)
        unique_count = int(unique_counts[col])

        # Characterize Moments for Numerical Data
        if col_str in numeric_df.columns:
            series = numeric_df[col_str].dropna()
            if not series.empty:
                moments[col_str] = {
                    "mean": float(series.mean()),
                    "variance": float(series.var()),
                    "skewness": float(series.skew()),
                    "kurtosis": float(series.kurt())
                }

                # Check for 3rd and 4th moment issues
                if abs(moments[col_str]["skewness"]) > 2:
                    warnings.append(f"Column '{col_str}' has significant skewness ({moments[col_str]['skewness']:.2f}).")
                if abs(moments[col_str]["kurtosis"]) > 7:
                    warnings.append(f"Column '{col_str}' exhibits high kurtosis ({moments[col_str]['kurtosis']:.2f}) - potential fat-tail risk.")

        is_date_object = "date" in col_str.lower() and str(dtypes[col]) in ("object", "string")
        if null_pct > 10 and not is_date_object:
            warnings.append(f"Column '{col_str}' has high missing values ({null_pct}%).")

        try:
            sample_val = df[col_str].dropna().iloc[0] if not df[col_str].dropna().empty else ""
            sample = str(sample_val)[:50]
        except Exception:
            sample = ""

        cols.append({
            "name": col_str,
            "type": dtypes[col],
            "null_pct": null_pct,
            "unique": unique_count,
            "sample": sample,
        })

    total_nulls = int(null_counts_series.sum()) + int(df.duplicated().sum())
    total_cells = df.shape[0] * df.shape[1]
    completeness_score = (1 - total_nulls / max(total_cells, 1)) * 100
    quality_score = round((completeness_score * 0.6) + ((1 - int(df.duplicated().sum()) / max(row_count, 1)) * 40) - min(len(warnings) * 5, 25))
    quality_score = max(0, min(100, quality_score))

    return DataProfile(
        row_count=row_count,
        column_count=df.shape[1],
        columns=cols,
        null_counts=null_counts_series.to_dict(),
        quality_score=quality_score,
        warnings=warnings,
        numeric_summary=numeric_df.describe().to_dict() if not numeric_df.empty else {},
        moments=moments
    )

def quality_report(df: pd.DataFrame, key_columns: list[str]) -> dict[str, Any]:
    """Produce a simple quality report covering missing values and duplicates."""

    def _count_duplicate_rows(df: pd.DataFrame, keys: list[str]):
        full_dupes = df.duplicated(keep="first")
        key_dupes = df.duplicated(subset=keys, keep="first")
        return int((full_dupes & ~key_dupes).sum())

    return {
        "row_count": len(df),
        "missing_values": df.isna().sum().to_dict(),
        "duplicate_rows": _count_duplicate_rows(df, key_columns),
        "duplicate_keys": {col: int(df.duplicated(subset=[col]).sum()) for col in key_columns},
    }
