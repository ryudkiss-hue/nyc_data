"""Reusable dataframe sanitation for known NYC Open Data quality defects.

Centralizes the repairs applied before any analysis or visualization so the
Dash app, the PDF exporter, and ad-hoc scripts all see the same cleaned data:

- Placeholder / entry-error dates are nulled: values more than ``future_days``
  in the future (e.g. 2100-01-01 used upstream for "not yet certified") or
  before ``date_floor`` (pre-1990 entry errors).
- Exact full-row duplicates are dropped, comparing only hashable columns so
  geometry dicts/lists never break the check (they are kept in the data).
- Variables that are more than 90% missing are flagged in the report (kept in
  the frame — flagging is the caller's signal not to trust them citywide).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

DATE_FLOOR = pd.Timestamp("1990-01-01")
DEAD_VAR_THRESHOLD = 0.90


@dataclass
class SanitationReport:
    rows_in: int = 0
    rows_out: int = 0
    dupes_removed: int = 0
    bad_dates_nulled: int = 0
    bad_date_cols: list[str] = field(default_factory=list)
    dead_vars: list[str] = field(default_factory=list)
    pct_missing: float = 0.0


def _hashable_columns(df: pd.DataFrame) -> list[str]:
    return [
        c for c in df.columns
        if not df[c].dropna().head(20).map(lambda v: isinstance(v, (dict, list))).any()
    ]


def sanitize_dataframe(
    df: pd.DataFrame,
    *,
    future_days: int = 365,
    date_floor: pd.Timestamp = DATE_FLOOR,
    drop_duplicates: bool = True,
) -> tuple[pd.DataFrame, SanitationReport]:
    """Return a repaired copy of ``df`` plus a report of what was done."""
    report = SanitationReport(rows_in=len(df), rows_out=len(df))
    if df.empty:
        return df, report

    hashable = _hashable_columns(df)

    if drop_duplicates and hashable:
        before = len(df)
        subset = df[hashable]
        try:
            # Fast native path (C-level hashing). Falls back to string coercion
            # only if an unhashable value slipped past the column screen —
            # astype(str) on a wide frame is orders of magnitude slower.
            mask = subset.duplicated()
        except TypeError:
            mask = subset.astype(str).duplicated()
        df = df.loc[~mask].copy()
        report.dupes_removed = before - len(df)
    else:
        df = df.copy()

    now = pd.Timestamp.now()
    horizon = now + pd.Timedelta(days=future_days)
    for c in df.columns:
        if "date" not in c.lower():
            continue
        parsed = pd.to_datetime(df[c], errors="coerce", utc=True).dt.tz_localize(None)
        if parsed.notna().sum() == 0:
            continue
        bad = (parsed > horizon) | (parsed < date_floor)
        n_bad = int(bad.sum())
        if n_bad:
            df.loc[bad, c] = None
            report.bad_dates_nulled += n_bad
            report.bad_date_cols.append(f"{c} ({n_bad})")

    n = len(df)
    nulls = df[hashable].isna().sum() if hashable else pd.Series(dtype=int)
    for c in df.select_dtypes(include=["object"]).columns:
        if c in hashable:
            nulls[c] = nulls.get(c, 0) + int((df[c].astype(str).str.strip() == "").sum())
    if hashable and n:
        report.pct_missing = round(100 * float(nulls.sum()) / (n * len(hashable)), 1)
        report.dead_vars = [
            f"{c} ({100 * v / n:.0f}%)" for c, v in nulls.items()
            if v / n > DEAD_VAR_THRESHOLD
        ]
    report.rows_out = n
    return df, report
