"""Change Detection for DOT Sidewalk Toolkit.

Compare two data snapshots (yesterday vs today) and surface differences:
new records, removed records, status changes, and field modifications.

Example::

    from socrata_toolkit.pipeline.cdc import detect_changes

    changes = detect_changes(old_df, new_df, key_col="id")
    print(f"Added: {changes.added_count}, Removed: {changes.removed_count}, Modified: {changes.modified_count}")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class FieldChange:
    """A single field change on a record."""
    key: Any
    field: str
    old_value: Any
    new_value: Any


@dataclass
class ChangeReport:
    """Results from comparing two data snapshots."""
    added_count: int
    removed_count: int
    modified_count: int
    unchanged_count: int
    total_field_changes: int
    added_keys: list[Any]
    removed_keys: list[Any]
    field_changes: list[FieldChange]
    summary_by_field: dict[str, int]
    added_df: pd.DataFrame
    removed_df: pd.DataFrame
    modified_df: pd.DataFrame


def detect_changes(
    old_df: pd.DataFrame,
    new_df: pd.DataFrame,
    key_col: str = "id",
    compare_cols: list[str] | None = None,
    ignore_cols: list[str] | None = None,
) -> ChangeReport:
    """Compare two DataFrames and return a detailed change report.

    Args:
        old_df: Previous snapshot.
        new_df: Current snapshot.
        key_col: Column used as unique identifier for row matching.
        compare_cols: Columns to compare (default: all shared columns).
        ignore_cols: Columns to skip during comparison.
    """
    ignore = set(ignore_cols or [])
    old_keys = set(old_df[key_col]) if key_col in old_df.columns else set()
    new_keys = set(new_df[key_col]) if key_col in new_df.columns else set()

    added_keys = sorted(new_keys - old_keys)
    removed_keys = sorted(old_keys - new_keys)
    common_keys = old_keys & new_keys

    # DataFrames for added/removed
    added_df = new_df[new_df[key_col].isin(added_keys)].reset_index(drop=True)
    removed_df = old_df[old_df[key_col].isin(removed_keys)].reset_index(drop=True)

    # Field-level comparison
    shared_cols = set(old_df.columns) & set(new_df.columns) - {key_col} - ignore
    if compare_cols:
        shared_cols = set(compare_cols) & shared_cols
    shared_cols = sorted(shared_cols)

    field_changes: list[FieldChange] = []
    summary_by_field: dict[str, int] = {c: 0 for c in shared_cols}
    modified_keys_set: set = set()

    old_indexed = old_df.set_index(key_col) if key_col in old_df.columns else pd.DataFrame()
    new_indexed = new_df.set_index(key_col) if key_col in new_df.columns else pd.DataFrame()

    for key in common_keys:
        if key not in old_indexed.index or key not in new_indexed.index:
            continue
        old_row = old_indexed.loc[key]
        new_row = new_indexed.loc[key]

        # Handle duplicate keys: take first row
        if isinstance(old_row, pd.DataFrame):
            old_row = old_row.iloc[0]
        if isinstance(new_row, pd.DataFrame):
            new_row = new_row.iloc[0]

        for col in shared_cols:
            old_val = old_row.get(col)
            new_val = new_row.get(col)
            if _values_differ(old_val, new_val):
                field_changes.append(FieldChange(key=key, field=col, old_value=old_val, new_value=new_val))
                summary_by_field[col] = summary_by_field.get(col, 0) + 1
                modified_keys_set.add(key)

    modified_df = new_df[new_df[key_col].isin(modified_keys_set)].reset_index(drop=True)

    return ChangeReport(
        added_count=len(added_keys),
        removed_count=len(removed_keys),
        modified_count=len(modified_keys_set),
        unchanged_count=len(common_keys) - len(modified_keys_set),
        total_field_changes=len(field_changes),
        added_keys=added_keys,
        removed_keys=removed_keys,
        field_changes=field_changes,
        summary_by_field={k: v for k, v in summary_by_field.items() if v > 0},
        added_df=added_df,
        removed_df=removed_df,
        modified_df=modified_df,
    )


def _values_differ(a: Any, b: Any) -> bool:
    if pd.isna(a) and pd.isna(b):
        return False
    if pd.isna(a) or pd.isna(b):
        return True
    return str(a) != str(b)


def detect_status_changes(
    old_df: pd.DataFrame,
    new_df: pd.DataFrame,
    key_col: str = "id",
    status_col: str = "status",
) -> pd.DataFrame:
    """Focused comparison: find records where status changed.

    Returns a DataFrame with key, old_status, new_status columns.
    """
    changes = detect_changes(old_df, new_df, key_col=key_col, compare_cols=[status_col])
    if not changes.field_changes:
        return pd.DataFrame(columns=[key_col, "old_status", "new_status"])

    rows = [
        {key_col: c.key, "old_status": c.old_value, "new_status": c.new_value}
        for c in changes.field_changes if c.field == status_col
    ]
    return pd.DataFrame(rows)
