"""Tests for socrata_toolkit.privacy.lineage_guard."""

from __future__ import annotations

import pandas as pd

from socrata_toolkit.privacy import masking
from socrata_toolkit.privacy.lineage_guard import (
    mask_pii_columns,
    redact_column_names,
)
from socrata_toolkit.privacy.pii_scanner import scan_dataframe


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "email": ["alice@example.com", "bob@test.org", "carol@mail.net"],
            "ssn": ["123-45-6789", "987-65-4321", "555-44-3333"],
            "amount": [100, 200, 300],
        }
    )


def test_pii_columns_masked_non_pii_untouched():
    df = _frame()
    masked, report = mask_pii_columns(df)

    assert "email" in report
    assert "ssn" in report
    # non-PII numeric column left alone
    assert "amount" not in report
    assert list(masked["amount"]) == list(df["amount"])

    # values actually changed for flagged columns
    assert list(masked["email"]) != list(df["email"])
    assert list(masked["ssn"]) != list(df["ssn"])


def test_report_names_expected_strategies():
    df = _frame()
    _, report = mask_pii_columns(df)
    assert report["email"] == masking.PARTIAL_MASK
    assert report["ssn"] == masking.HASH_TOKEN


def test_redact_column_names_pseudonymizes_only_flagged():
    df = _frame()
    signals = scan_dataframe(df)
    redacted = redact_column_names(list(df.columns), signals)

    flagged = {s.column for s in signals}
    assert "amount" in redacted  # non-PII kept
    for name, new in zip(df.columns, redacted, strict=False):
        if name in flagged:
            assert new.startswith("pii_col_")
        else:
            assert new == name
    # pseudonyms are distinct and stable
    pii_names = [n for n in redacted if n.startswith("pii_col_")]
    assert len(set(pii_names)) == len(pii_names)
