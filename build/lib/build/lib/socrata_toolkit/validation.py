from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class ValidationReport:
    valid: bool
    errors: list[str]
    warnings: list[str]


def validate_required_columns(df: pd.DataFrame, required: list[str]) -> ValidationReport:
    missing = [c for c in required if c not in df.columns]
    errors = [f"Missing required column: {c}" for c in missing]
    return ValidationReport(valid=not errors, errors=errors, warnings=[])


def validate_schema_types(df: pd.DataFrame, schema: dict[str, str]) -> ValidationReport:
    errors: list[str] = []
    warns: list[str] = []
    for c, expected in schema.items():
        if c not in df.columns:
            errors.append(f"Missing expected column: {c}")
            continue
        actual = str(df[c].dtype)
        if expected not in actual:
            warns.append(f"Column {c}: expected {expected}, got {actual}")
    return ValidationReport(valid=not errors, errors=errors, warnings=warns)
