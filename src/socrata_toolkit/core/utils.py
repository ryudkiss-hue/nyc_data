from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    import pandas as pd


class SocrataToolkitError(Exception):
    pass


def with_retries(fn: Callable[[], requests.Response], retries: int = 3, backoff: float = 1.5) -> requests.Response:
    last_exc: Exception | None = None
    delay = 1.0
    for _ in range(retries):
        try:
            resp = fn()
            resp.raise_for_status()
            return resp
        except Exception as exc:  # network/server surface as clean toolkit error later
            last_exc = exc
            time.sleep(delay)
            delay *= backoff
    raise SocrataToolkitError(f"Request failed after {retries} retries: {last_exc}")


def normalize_formats(values: list[str]) -> list[str]:
    return [v.strip().lower() for v in values if v and v.strip()]


# ---------------------------------------------------------------------------
# Date coercion helpers
# ---------------------------------------------------------------------------


def coerce_datetime_column(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Return a copy of *df* with *col* coerced to datetime (errors -> NaT).

    This is a thin wrapper around ``pd.to_datetime(..., errors='coerce')`` that
    eliminates the repetitive in-place assignment scattered across analysis and
    visualisation modules.
    """
    import pandas as pd

    out = df.copy()
    if col in out.columns:
        out[col] = pd.to_datetime(out[col], errors="coerce")
    return out


def coerce_datetime_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Coerce multiple columns to datetime in a single call."""
    import pandas as pd

    out = df.copy()
    for col in cols:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    return out


def coerce_series_datetime(series: pd.Series) -> pd.Series:
    """Coerce a Series to datetime, converting bad values to NaT.

    Drop-in replacement for the repeated pattern
    ``pd.to_datetime(series, errors="coerce")`` across analysis modules.
    """
    import pandas as pd

    return pd.to_datetime(series, errors="coerce")


# ---------------------------------------------------------------------------
# Borough normalisation helpers
# ---------------------------------------------------------------------------

#: Canonical ordered list of NYC boroughs used across the toolkit.
BOROUGH_LIST: list[str] = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]

#: Set form for fast membership tests.
BOROUGH_SET: frozenset[str] = frozenset(BOROUGH_LIST)

#: Mapping of common abbreviations / alternate names -> canonical title-case.
_BOROUGH_ALIASES: dict[str, str] = {
    # numeric codes
    "1": "Manhattan",
    "2": "Bronx",
    "3": "Brooklyn",
    "4": "Queens",
    "5": "Staten Island",
    # abbreviations
    "MN": "Manhattan",
    "BX": "Bronx",
    "BK": "Brooklyn",
    "QN": "Queens",
    "SI": "Staten Island",
    # alternate names
    "NEW YORK": "Manhattan",
    "KINGS": "Brooklyn",
    "RICHMOND": "Staten Island",
    "THE BRONX": "Bronx",
    # uppercase canonical forms
    "MANHATTAN": "Manhattan",
    "BRONX": "Bronx",
    "BROOKLYN": "Brooklyn",
    "QUEENS": "Queens",
    "STATEN ISLAND": "Staten Island",
}


def normalize_borough(value: str) -> str:
    """Normalise a raw borough string to its canonical title-case form.

    Returns ``"Unknown"`` for unrecognised values rather than raising.

    Examples::

        normalize_borough("BX")           # -> "Bronx"
        normalize_borough("the bronx")    # -> "Bronx"
        normalize_borough("KINGS")        # -> "Brooklyn"
        normalize_borough("gibberish")    # -> "Unknown"
    """
    return _BOROUGH_ALIASES.get(value.strip().upper(), "Unknown")
