"""Declarative data contracts for DataFrame validation.

Provides field- and dataset-level contracts that validate a pandas DataFrame
against presence, null policy, dtype, bounds, allowed values, regex,
uniqueness, and primary-key rules. Contracts are declarable in YAML.
"""

from __future__ import annotations

from .core import (
    ContractViolation,
    DataContract,
    FieldContract,
    ValidationResult,
)

__all__ = [
    "FieldContract",
    "DataContract",
    "ContractViolation",
    "ValidationResult",
]
