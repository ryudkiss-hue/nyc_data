from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class DataProfile:
    row_count: int
    column_count: int
    null_counts: dict[str, int]
    dtypes: dict[str, str]
    numeric_summary: dict[str, dict[str, float]]


def to_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def profile_dataframe(df: pd.DataFrame) -> DataProfile:
    numeric = df.select_dtypes(include=["number"])
    numeric_summary: dict[str, dict[str, float]] = {}
    if not numeric.empty:
        desc = numeric.describe().fillna(0)
        for col in desc.columns:
            numeric_summary[col] = {
                "min": float(desc[col].get("min", 0)),
                "max": float(desc[col].get("max", 0)),
                "mean": float(desc[col].get("mean", 0)),
                "std": float(desc[col].get("std", 0)),
            }
    return DataProfile(
        row_count=len(df),
        column_count=len(df.columns),
        null_counts={c: int(df[c].isna().sum()) for c in df.columns},
        dtypes={c: str(t) for c, t in df.dtypes.items()},
        numeric_summary=numeric_summary,
    )


def quality_report(df: pd.DataFrame, key_columns: list[str] | None = None) -> dict[str, Any]:
    key_columns = key_columns or []
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
    # Count duplicate rows, but if key columns are provided exclude rows
    # that are duplicates on the key columns (those are reported in
    # `duplicate_keys` instead).
    if key_columns:
        # remove rows that are duplicates by key columns (keep first)
        df_no_key_dups = df.drop_duplicates(subset=key_columns)
        duplicate_rows = int(df_no_key_dups.duplicated().sum())
    else:
        duplicate_rows = int(df.duplicated().sum())
=======
    duplicate_rows = int(df.duplicated().sum())
>>>>>>> theirs
=======
    duplicate_rows = int(df.duplicated().sum())
>>>>>>> theirs
=======
    duplicate_rows = int(df.duplicated().sum())
>>>>>>> theirs
    duplicate_keys = {}
    for key in key_columns:
        if key in df.columns:
            duplicate_keys[key] = int(df[key].duplicated().sum())
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "duplicate_rows": duplicate_rows,
        "duplicate_keys": duplicate_keys,
        "missing_cells": int(df.isna().sum().sum()),
    }
