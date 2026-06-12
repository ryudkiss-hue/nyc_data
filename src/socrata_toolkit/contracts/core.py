"""Data-contract validation against pandas DataFrames.

Defines declarable field-level contracts (:class:`FieldContract`) grouped into
a :class:`DataContract`, and validates a DataFrame against them, accumulating
:class:`ContractViolation` records (one per rule, with a violation ``count``)
into a :class:`ValidationResult`. Contracts round-trip through dict and YAML so
they can live alongside the project's other declarative config.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

# Supported logical dtypes for parseability checks.
_DTYPES = {"int", "float", "str", "bool", "datetime"}

_BOOL_TRUE = {"true", "1", "yes", "y", "t"}
_BOOL_FALSE = {"false", "0", "no", "n", "f"}

@dataclass
class FieldContract:
    """Declarative expectations for a single field/column.

    Attributes:
        name: Column name.
        dtype: Logical type (``int``, ``float``, ``str``, ``bool``, ``datetime``).
        required: Whether the column must be present.
        nullable: Whether null values are allowed.
        min: Optional inclusive numeric lower bound.
        max: Optional inclusive numeric upper bound.
        allowed: Optional set/list of allowed values.
        regex: Optional regex every (non-null) value must fully match.
        unique: Whether values must be unique.
    """

    name: str
    dtype: str
    required: bool = True
    nullable: bool = False
    min: float | None = None
    max: float | None = None
    allowed: list[Any] | None = None
    regex: str | None = None
    unique: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FieldContract:
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})

@dataclass
class ContractViolation:
    """A single failed rule for a field.

    Attributes:
        field: Column name (or ``"<primary_key>"`` for PK rules).
        rule: Rule identifier (e.g. ``required``, ``nullable``, ``dtype``).
        detail: Human-readable description of the failure.
        count: Number of offending rows (1 for presence/structural rules).
    """

    field: str
    rule: str
    detail: str
    count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class ValidationResult:
    """Outcome of validating a DataFrame against a :class:`DataContract`."""

    passed: bool
    violations: list[ContractViolation] = field(default_factory=list)
    rows_checked: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
            "rows_checked": self.rows_checked,
        }

def _parseable_mask(series: pd.Series, dtype: str) -> pd.Series:
    """Boolean mask of non-null values that parse as ``dtype``."""
    non_null = series.dropna()
    if non_null.empty:
        return pd.Series([], dtype=bool)

    if dtype == "int":
        coerced = pd.to_numeric(non_null, errors="coerce")
        ok = coerced.notna() & (coerced.astype("float") % 1 == 0)
        return ok
    if dtype == "float":
        return pd.to_numeric(non_null, errors="coerce").notna()
    if dtype == "bool":
        def is_bool(v: Any) -> bool:
            if isinstance(v, bool):
                return True
            return str(v).strip().lower() in _BOOL_TRUE | _BOOL_FALSE
        return non_null.map(is_bool)
    if dtype == "datetime":
        return pd.to_datetime(non_null, errors="coerce").notna()
    # str: anything stringifiable parses
    return pd.Series(True, index=non_null.index)

@dataclass
class DataContract:
    """A named collection of field contracts plus an optional primary key."""

    name: str
    fields: list[FieldContract] = field(default_factory=list)
    primary_key: list[str] | None = None

    # --- validation ---
    def validate(self, df: pd.DataFrame) -> ValidationResult:
        """Validate ``df`` against this contract, accumulating all violations."""
        violations: list[ContractViolation] = []

        for fc in self.fields:
            present = fc.name in df.columns
            if not present:
                if fc.required:
                    violations.append(
                        ContractViolation(
                            fc.name, "required",
                            f"required column '{fc.name}' is missing", 1,
                        )
                    )
                continue

            series = df[fc.name]

            # null policy
            null_count = int(series.isna().sum())
            if not fc.nullable and null_count:
                violations.append(
                    ContractViolation(
                        fc.name, "nullable",
                        f"column '{fc.name}' has {null_count} null value(s)",
                        null_count,
                    )
                )

            # dtype parseability (non-null only)
            if fc.dtype in _DTYPES:
                ok = _parseable_mask(series, fc.dtype)
                bad = int((~ok).sum()) if len(ok) else 0
                if bad:
                    violations.append(
                        ContractViolation(
                            fc.name, "dtype",
                            f"{bad} value(s) in '{fc.name}' not parseable as {fc.dtype}",
                            bad,
                        )
                    )

            # numeric bounds
            if fc.min is not None or fc.max is not None:
                numeric = pd.to_numeric(series, errors="coerce").dropna()
                if fc.min is not None:
                    below = int((numeric < fc.min).sum())
                    if below:
                        violations.append(
                            ContractViolation(
                                fc.name, "min",
                                f"{below} value(s) in '{fc.name}' below min {fc.min}",
                                below,
                            )
                        )
                if fc.max is not None:
                    above = int((numeric > fc.max).sum())
                    if above:
                        violations.append(
                            ContractViolation(
                                fc.name, "max",
                                f"{above} value(s) in '{fc.name}' above max {fc.max}",
                                above,
                            )
                        )

            # allowed-value set
            if fc.allowed is not None:
                allowed = set(fc.allowed)
                non_null = series.dropna()
                disallowed = int((~non_null.isin(allowed)).sum())
                if disallowed:
                    violations.append(
                        ContractViolation(
                            fc.name, "allowed",
                            f"{disallowed} value(s) in '{fc.name}' not in allowed set",
                            disallowed,
                        )
                    )

            # regex conformance
            if fc.regex is not None:
                pattern = re.compile(fc.regex)
                non_null = series.dropna()
                mismatch = int(
                    non_null.map(lambda v: pattern.fullmatch(str(v)) is None).sum()
                )
                if mismatch:
                    violations.append(
                        ContractViolation(
                            fc.name, "regex",
                            f"{mismatch} value(s) in '{fc.name}' do not match regex",
                            mismatch,
                        )
                    )

            # uniqueness
            if fc.unique:
                non_null = series.dropna()
                dup = int(non_null.duplicated(keep=False).sum())
                if dup:
                    violations.append(
                        ContractViolation(
                            fc.name, "unique",
                            f"{dup} non-unique value(s) in '{fc.name}'",
                            dup,
                        )
                    )

        # primary key
        if self.primary_key:
            missing_cols = [c for c in self.primary_key if c not in df.columns]
            if missing_cols:
                violations.append(
                    ContractViolation(
                        "<primary_key>", "primary_key",
                        f"primary key column(s) missing: {missing_cols}",
                        len(missing_cols),
                    )
                )
            else:
                pk = df[self.primary_key]
                null_rows = int(pk.isna().any(axis=1).sum())
                if null_rows:
                    violations.append(
                        ContractViolation(
                            "<primary_key>", "primary_key",
                            f"{null_rows} row(s) with null primary key value(s)",
                            null_rows,
                        )
                    )
                dup_rows = int(pk.duplicated(keep=False).sum())
                if dup_rows:
                    violations.append(
                        ContractViolation(
                            "<primary_key>", "primary_key",
                            f"{dup_rows} row(s) with duplicate primary key",
                            dup_rows,
                        )
                    )

        return ValidationResult(
            passed=not violations,
            violations=violations,
            rows_checked=len(df),
        )

    # --- serialization ---
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "fields": [f.to_dict() for f in self.fields],
            "primary_key": list(self.primary_key) if self.primary_key else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DataContract:
        raw_fields = data.get("fields", []) or []
        fields_ = [
            f if isinstance(f, FieldContract) else FieldContract.from_dict(f)
            for f in raw_fields
        ]
        return cls(
            name=str(data.get("name", "")),
            fields=fields_,
            primary_key=data.get("primary_key"),
        )

    def to_yaml(self, path: str | Path | None = None) -> str:
        """Serialize to YAML; write to ``path`` if given, return the text."""
        text = yaml.safe_dump(self.to_dict(), sort_keys=False)
        if path is not None:
            Path(path).write_text(text, encoding="utf-8")
        return text

    @classmethod
    def from_yaml(cls, path: str | Path) -> DataContract:
        """Load a contract from a YAML file."""
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls.from_dict(data)
