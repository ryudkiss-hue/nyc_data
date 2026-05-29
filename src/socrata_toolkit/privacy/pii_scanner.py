"""
PII Scanner - Multi-signal personally-identifiable-information detection.

A standalone, rigorous scanner that combines three independent signals to
detect PII in a pandas DataFrame:

1. Column-name heuristics (semantic guesses from the column label).
2. Value regex / format patterns (email, US phone, SSN, credit-card w/ Luhn, IP).
3. Value-entropy / uniqueness heuristics (near-unique high-cardinality strings
   are flagged as possible identifiers).

Signals are combined into a confidence score in [0, 1] and a severity is
assigned per PII kind. This module is intentionally dependency-light
(stdlib + pandas + numpy) and does not modify or rely on the legacy helper in
``api/governance.py``.

Standards: Python 3.9+, full type hints, concise docstrings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Severity mapping per PII kind.
# --------------------------------------------------------------------------- #
_SEVERITY_BY_KIND: dict[str, str] = {
    "ssn": "critical",
    "credit_card": "critical",
    "passport": "critical",
    "email": "high",
    "phone": "high",
    "license": "high",
    "dob": "high",
    "name": "medium",
    "address": "medium",
    "ip": "medium",
    "geo": "medium",
    "identifier": "low",
}

_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}

# --------------------------------------------------------------------------- #
# Column-name heuristics: kind -> regex over the (lower-cased) column name.
# --------------------------------------------------------------------------- #
_NAME_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"e[-_]?mail"),
    "phone": re.compile(r"phone|mobile|cell|fax|telephone"),
    "ssn": re.compile(r"ssn|social.?sec|social_security"),
    "dob": re.compile(r"\b(dob|birth)\b|date_of_birth|birth_?date|birthday"),
    "name": re.compile(r"(first|last|full|middle|sur|given)?_?name\b|fullname|surname"),
    "address": re.compile(r"address|street|zip|postal|city\b"),
    "license": re.compile(r"licen[sc]e|drivers?_?lic"),
    "passport": re.compile(r"passport"),
    "credit_card": re.compile(r"credit.?card|card_?(no|num|number)|ccn\b"),
    "geo": re.compile(r"\b(lat|latitude|lon|lng|long|longitude)\b"),
    "ip": re.compile(r"\bip(_?addr(ess)?)?\b"),
}

# --------------------------------------------------------------------------- #
# Value regex patterns.
# --------------------------------------------------------------------------- #
_VALUE_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$"),
    "phone": re.compile(
        r"^\+?1?[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}$"
    ),
    "ssn": re.compile(r"^\d{3}-\d{2}-\d{4}$"),
    "ip": re.compile(
        r"^(\d{1,3}\.){3}\d{1,3}$"
    ),
}

_CARD_CANDIDATE = re.compile(r"^[\d \-]{13,23}$")


@dataclass
class PiiSignal:
    """A detected PII signal for a single column.

    Attributes:
        column: Source column name.
        kind: PII kind (e.g. ``email``, ``ssn``, ``credit_card``, ``name`` ...).
        confidence: Combined confidence score in [0, 1].
        evidence: Human-readable strings describing which signals fired.
        severity: One of ``low``, ``medium``, ``high``, ``critical``.
    """

    column: str
    kind: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    severity: str = "low"


def luhn_check(number: str) -> bool:
    """Validate a candidate credit-card number with the Luhn algorithm.

    The Luhn (mod-10) checksum: starting from the rightmost digit, double every
    second digit; if doubling yields a value > 9 subtract 9; the total of all
    resulting digits must be divisible by 10.

    Args:
        number: A string that may contain spaces/dashes; non-digits are stripped.

    Returns:
        True if the digit string passes the Luhn check (and has 13-19 digits).
    """
    digits = [int(c) for c in re.sub(r"[\s-]", "", number) if c.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _clean_values(series: pd.Series) -> list[str]:
    """Return non-null values as stripped strings."""
    return [str(v).strip() for v in series.dropna().tolist() if str(v).strip()]


def _value_match_ratio(values: list[str], kind: str) -> float:
    """Fraction of values matching the regex/format for ``kind``."""
    if not values:
        return 0.0
    if kind == "credit_card":
        hits = sum(
            1 for v in values if _CARD_CANDIDATE.match(v) and luhn_check(v)
        )
        return hits / len(values)
    pattern = _VALUE_PATTERNS.get(kind)
    if pattern is None:
        return 0.0
    if kind == "ip":
        def ok(v: str) -> bool:
            if not pattern.match(v):
                return False
            return all(0 <= int(p) <= 255 for p in v.split("."))
        return sum(1 for v in values if ok(v)) / len(values)
    return sum(1 for v in values if pattern.match(v)) / len(values)


def _name_signal(column: str) -> list[tuple[str, str]]:
    """Return (kind, evidence) tuples for column-name matches."""
    col = column.strip().lower()
    out: list[tuple[str, str]] = []
    for kind, pattern in _NAME_PATTERNS.items():
        if pattern.search(col):
            out.append((kind, f"column name matches {kind} heuristic"))
    return out


def _uniqueness_signal(series: pd.Series, values: list[str]) -> float:
    """High-cardinality near-unique string columns -> identifier likelihood.

    Returns a ratio of distinct values to total non-null values; values close
    to 1.0 on a sufficiently large column suggest a free-form identifier.
    """
    n = len(values)
    if n < 5:
        return 0.0
    distinct = series.dropna().nunique()
    return distinct / n


def scan_dataframe(df: pd.DataFrame) -> list[PiiSignal]:
    """Scan a DataFrame and return one :class:`PiiSignal` per flagged column.

    Combines column-name heuristics, value-format regex (incl. Luhn for cards),
    and an entropy/uniqueness heuristic. For each column the strongest detected
    kind is reported. Confidence is computed as a weighted blend:

    - value-format match ratio contributes up to 0.7,
    - column-name match contributes 0.4,
    - capped at 1.0; a pure name match yields ~0.4, a name match confirmed by
      values approaches 1.0.

    Args:
        df: Input pandas DataFrame.

    Returns:
        A list of detected signals (possibly empty), highest severity first.
    """
    signals: list[PiiSignal] = []

    for column in df.columns:
        series = df[column]
        values = _clean_values(series)
        if not values:
            continue

        # Per-kind accumulation of confidence + evidence.
        candidates: dict[str, tuple[float, list[str]]] = {}

        def add(kind: str, conf: float, ev: str) -> None:
            prev_conf, prev_ev = candidates.get(kind, (0.0, []))
            candidates[kind] = (min(1.0, prev_conf + conf), prev_ev + [ev])

        # (a) column-name heuristics
        name_kinds = {k for k, _ in _name_signal(column)}
        for kind, ev in _name_signal(column):
            add(kind, 0.4, ev)

        # (b) value-format regex (incl. Luhn for cards)
        for kind in ("email", "phone", "ssn", "ip", "credit_card"):
            ratio = _value_match_ratio(values, kind)
            if ratio > 0:
                # weight by prevalence; a confirming name match already present
                add(kind, min(0.7, 0.7 * ratio + (0.2 if ratio >= 0.5 else 0.0)),
                    f"{ratio:.0%} of values match {kind} format")

        # (c) entropy / uniqueness heuristic -> generic identifier
        is_stringy = series.dropna().map(lambda v: isinstance(v, str)).mean() if len(values) else 0
        uniq = _uniqueness_signal(series, values)
        if uniq >= 0.95 and is_stringy > 0.5 and not name_kinds:
            # only flag as bare identifier if no stronger semantic signal exists
            add("identifier", min(0.5, uniq * 0.5),
                f"near-unique high-cardinality string column ({uniq:.0%} distinct)")

        if not candidates:
            continue

        # pick the highest-severity, then highest-confidence kind
        def sort_key(item: tuple[str, tuple[float, list[str]]]):
            kind, (conf, _) = item
            return (_SEVERITY_RANK[_SEVERITY_BY_KIND[kind]], conf)

        best_kind, (best_conf, best_ev) = max(candidates.items(), key=sort_key)
        signals.append(
            PiiSignal(
                column=str(column),
                kind=best_kind,
                confidence=round(float(best_conf), 4),
                evidence=best_ev,
                severity=_SEVERITY_BY_KIND[best_kind],
            )
        )

    signals.sort(
        key=lambda s: (_SEVERITY_RANK[s.severity], s.confidence), reverse=True
    )
    return signals
