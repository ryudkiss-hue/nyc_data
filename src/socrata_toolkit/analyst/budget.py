"""Optional budget code validation for analyst packs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def load_budget_rules(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def validate_budget_codes(
    contracts: pd.DataFrame,
    rules: dict[str, Any],
    *,
    code_col: str = "budget_code",
) -> list[str]:
    """Return warning strings for invalid or missing budget codes."""
    warnings: list[str] = []
    if not rules or contracts.empty:
        return warnings

    allowed = set(rules.get("allowed_codes", []))
    required = bool(rules.get("require_code", False))
    if not allowed and not required:
        return warnings

    if code_col not in contracts.columns:
        if required:
            warnings.append(f"Budget validation: column '{code_col}' missing from contracts")
        return warnings

    for val in contracts[code_col].dropna().astype(str).unique():
        if val not in allowed:
            warnings.append(f"Budget code not in allowlist: {val}")

    missing = int(contracts[code_col].isna().sum())
    if required and missing:
        warnings.append(f"Budget validation: {missing} row(s) missing budget_code")

    return warnings
