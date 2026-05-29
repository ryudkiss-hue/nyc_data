"""
Masking strategies for PII columns.

Each strategy operates on a pandas Series (or scalar where noted) and returns a
transformed Series. Reversibility is documented per strategy:

- ``redact``       : irreversible (information destroyed).
- ``hash_token``   : irreversible (one-way SHA-256; deterministic with salt).
- ``bucket_numeric``: lossy (values collapsed into ranges; not recoverable).
- ``truncate_geo`` : lossy (precision reduced by rounding).
- ``partial_mask`` : irreversible for the masked portion (last N kept).

Standards: Python 3.9+, full type hints, concise docstrings.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from .pii_scanner import PiiSignal


def redact(series: pd.Series, token: str = "***") -> pd.Series:
    """Replace every non-null value with a fixed token. Irreversible.

    Args:
        series: Input series.
        token: Replacement string (default ``***``).

    Returns:
        Series of the same index with values redacted (nulls preserved).
    """
    return series.map(lambda v: token if pd.notna(v) else v)


def hash_token(series: pd.Series, salt: str = "") -> pd.Series:
    """Deterministically tokenise values via salted SHA-256. Irreversible.

    The same (value, salt) pair always yields the same 64-char hex token, so
    joins on the tokenised column remain valid while the original value cannot
    be recovered.

    Args:
        series: Input series.
        salt: Salt mixed into the digest; change the salt to rotate tokens.

    Returns:
        Series of hex digest strings (nulls preserved).
    """
    def _hash(v: object) -> object:
        if pd.isna(v):
            return v
        digest = hashlib.sha256((salt + str(v)).encode("utf-8"))
        return digest.hexdigest()

    return series.map(_hash)


def bucket_numeric(series: pd.Series, bins: int = 5) -> pd.Series:
    """Collapse numeric values into ``bins`` equal-width range buckets. Lossy.

    Args:
        series: Numeric input series.
        bins: Number of equal-width buckets.

    Returns:
        Series of interval-label strings like ``"[0.0, 10.0)"`` (nulls preserved).
    """
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() == 0:
        return series.map(lambda v: v)
    lo, hi = float(numeric.min()), float(numeric.max())
    if lo == hi:
        # single value -> one bucket
        return numeric.map(lambda v: f"[{lo}, {hi}]" if pd.notna(v) else v)
    edges = np.linspace(lo, hi, bins + 1)

    def _bucket(v: float) -> object:
        if pd.isna(v):
            return v
        idx = int(np.clip(np.searchsorted(edges, v, side="right") - 1, 0, bins - 1))
        left, right = edges[idx], edges[idx + 1]
        closing = "]" if idx == bins - 1 else ")"
        return f"[{left:.4g}, {right:.4g}{closing}"

    return numeric.map(_bucket)


def truncate_geo(series: pd.Series, precision: int = 2) -> pd.Series:
    """Round latitude/longitude values to ``precision`` decimals. Lossy.

    At precision=2 the location is coarsened to roughly ~1 km, reducing
    re-identification risk while preserving approximate position.

    Args:
        series: Numeric geo series.
        precision: Number of decimal places to keep.

    Returns:
        Series of rounded floats (nulls preserved).
    """
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.map(lambda v: round(float(v), precision) if pd.notna(v) else v)


def partial_mask(series: pd.Series, keep: int = 4, mask_char: str = "*") -> pd.Series:
    """Mask all but the last ``keep`` characters of each value. Irreversible.

    Args:
        series: Input series (coerced to string).
        keep: Number of trailing characters to leave visible.
        mask_char: Character used for the masked portion.

    Returns:
        Series of partially masked strings (nulls preserved).
    """
    def _mask(v: object) -> object:
        if pd.isna(v):
            return v
        s = str(v)
        if keep <= 0:
            return mask_char * len(s)
        if len(s) <= keep:
            return s
        return mask_char * (len(s) - keep) + s[-keep:]

    return series.map(_mask)


# Strategy name constants (the values returned by ``recommend_strategy``).
REDACT = "redact"
HASH_TOKEN = "hash_token"
BUCKET_NUMERIC = "bucket_numeric"
TRUNCATE_GEO = "truncate_geo"
PARTIAL_MASK = "partial_mask"


def recommend_strategy(signal: PiiSignal) -> str:
    """Recommend a masking strategy name for a detected PII signal.

    Mapping rationale:
    - Critical direct identifiers (SSN, credit card, passport) -> ``hash_token``
      (irreversible, preserves join-ability for de-duplication).
    - Geo coordinates -> ``truncate_geo`` (keep approximate location).
    - Emails/phones/licenses -> ``partial_mask`` (keep tail for support/UX).
    - Names/addresses -> ``redact`` (no useful partial value).
    - Generic high-cardinality identifiers -> ``hash_token``.

    Args:
        signal: A :class:`PiiSignal`.

    Returns:
        One of the strategy name constants defined in this module.
    """
    kind = signal.kind
    if kind in ("ssn", "credit_card", "passport", "identifier"):
        return HASH_TOKEN
    if kind == "geo":
        return TRUNCATE_GEO
    if kind in ("email", "phone", "license", "ip", "dob"):
        return PARTIAL_MASK
    if kind in ("name", "address"):
        return REDACT
    # default by severity
    return HASH_TOKEN if signal.severity == "critical" else REDACT
