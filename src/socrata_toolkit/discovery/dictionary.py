"""Auto-Generated Data Dictionary for DOT Sidewalk Toolkit.

Automatically document every column in a dataset with examples,
null rates, types, and business definitions.

Example::

    from socrata_toolkit.discovery.dictionary import generate_data_dictionary

    dd = generate_data_dictionary(df, dataset_name="Sidewalk Inspections")
    dd.save("docs/data_dictionary.md")
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class ColumnProfile:
    """Profile for a single column."""
    name: str
    dtype: str
    null_count: int
    null_pct: float
    unique_count: int
    unique_pct: float
    sample_values: list[Any]
    min_value: Any | None = None
    max_value: Any | None = None
    mean_value: float | None = None
    description: str = ""


@dataclass
class DataDictionary:
    """Complete data dictionary for a dataset."""
    dataset_name: str
    row_count: int
    column_count: int
    columns: list[ColumnProfile]
    generated_at: str = ""

    def to_markdown(self) -> str:
        lines = [
            f"# Data Dictionary: {self.dataset_name}",
            "",
            f"**Rows:** {self.row_count:,} | **Columns:** {self.column_count}",
            "",
            "| Column | Type | Nulls | Unique | Sample | Description |",
            "|--------|------|-------|--------|--------|-------------|",
        ]
        for c in self.columns:
            samples = ", ".join(str(s) for s in c.sample_values[:3])
            desc = c.description or (f"Range: {c.min_value} to {c.max_value}" if c.min_value is not None else "")
            lines.append(f"| `{c.name}` | {c.dtype} | {c.null_pct:.1f}% | {c.unique_count} | {samples} | {desc} |")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": [c.__dict__ for c in self.columns],
        }

    def save(self, path: str) -> str:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix == ".json":
            import json
            p.write_text(json.dumps(self.to_dict(), indent=2, default=str), encoding="utf-8")
        else:
            p.write_text(self.to_markdown(), encoding="utf-8")
        return str(p)


def generate_data_dictionary(
    df: pd.DataFrame,
    dataset_name: str = "Dataset",
    descriptions: dict[str, str] | None = None,
) -> DataDictionary:
    """Generate a complete data dictionary from a DataFrame."""
    from datetime import datetime, timezone

    desc_map = descriptions or {}
    columns = []

    for col in df.columns:
        series = df[col]
        null_count = int(series.isna().sum())
        null_pct = round(null_count / max(len(df), 1) * 100, 1)
        unique = int(series.nunique(dropna=True))
        unique_pct = round(unique / max(len(df), 1) * 100, 1)
        samples = series.dropna().head(5).tolist()

        min_val = max_val = mean_val = None
        if pd.api.types.is_numeric_dtype(series):
            s = series.dropna()
            if not s.empty:
                min_val = float(s.min())
                max_val = float(s.max())
                mean_val = round(float(s.mean()), 4)

        columns.append(ColumnProfile(
            name=col,
            dtype=str(series.dtype),
            null_count=null_count,
            null_pct=null_pct,
            unique_count=unique,
            unique_pct=unique_pct,
            sample_values=samples,
            min_value=min_val,
            max_value=max_val,
            mean_value=mean_val,
            description=desc_map.get(col, ""),
        ))

    return DataDictionary(
        dataset_name=dataset_name,
        row_count=len(df),
        column_count=len(df.columns),
        columns=columns,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
