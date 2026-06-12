"""Privacy-preserving helpers for lineage / metadata export.

Wraps the PII scanner and masking strategies so a DataFrame can be exported
into lineage or metadata pipelines without leaking sensitive values or
column semantics: :func:`mask_pii_columns` masks flagged columns in place of
their original values, and :func:`redact_column_names` pseudonymizes the names
of flagged columns.
"""

from __future__ import annotations

import pandas as pd

from . import masking
from .pii_scanner import PiiSignal, scan_dataframe

# Map a recommended strategy name to its masking callable.
_STRATEGY_FUNCS = {
    masking.REDACT: masking.redact,
    masking.HASH_TOKEN: masking.hash_token,
    masking.BUCKET_NUMERIC: masking.bucket_numeric,
    masking.TRUNCATE_GEO: masking.truncate_geo,
    masking.PARTIAL_MASK: masking.partial_mask,
}

def mask_pii_columns(
    df: pd.DataFrame, signals: list[PiiSignal] | None = None
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Mask every PII-flagged column using its recommended strategy.

    Args:
        df: Input DataFrame.
        signals: Pre-computed PII signals; if ``None`` they are scanned from ``df``.

    Returns:
        A tuple ``(masked_df, report)`` where ``masked_df`` is a copy with
        flagged columns transformed and ``report`` maps ``{column: strategy}``.
    """
    if signals is None:
        signals = scan_dataframe(df)

    masked = df.copy()
    report: dict[str, str] = {}
    for sig in signals:
        if sig.column not in masked.columns:
            continue
        strategy = masking.recommend_strategy(sig)
        func = _STRATEGY_FUNCS.get(strategy, masking.redact)
        masked[sig.column] = func(masked[sig.column])
        report[sig.column] = strategy
    return masked, report

def redact_column_names(
    names: list[str], signals: list[PiiSignal]
) -> list[str]:
    """Pseudonymize PII-flagged column names for safe metadata export.

    Flagged names are replaced with a stable ``pii_col_<n>`` pseudonym (numbered
    by first appearance among flagged columns); non-flagged names are kept.

    Args:
        names: Ordered column names to transform.
        signals: PII signals identifying which columns are sensitive.

    Returns:
        A new list of names with flagged entries pseudonymized.
    """
    flagged = {s.column for s in signals}
    pseudonyms: dict[str, str] = {}
    out: list[str] = []
    for name in names:
        if name in flagged:
            if name not in pseudonyms:
                pseudonyms[name] = f"pii_col_{len(pseudonyms)}"
            out.append(pseudonyms[name])
        else:
            out.append(name)
    return out
