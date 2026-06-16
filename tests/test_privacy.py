"""Tests for socrata_toolkit.privacy (PII scanner, masking, DMBOK scoring)."""

from __future__ import annotations
import pytest


import pandas as pd
import pytest

from socrata_toolkit.privacy import (
    PiiSignal,
    bucket_numeric,
    hash_token,
    luhn_check,
    partial_mask,
    recommend_strategy,
    redact,
    scan_dataframe,
    score_dataframe,
    truncate_geo,
)

# A real Luhn-valid test card number (Visa test number).
VALID_CARD = "4111111111111111"
INVALID_CARD = "4111111111111112"

@pytest.fixture
def pii_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "full_name": ["Alice Smith", "Bob Jones", "Carol Lee"],
            "email": ["a@example.com", "b@test.org", "c@mail.net"],
            "phone": ["212-555-1234", "(646) 555-9999", "917.555.0000"],
            "ssn": ["123-45-6789", "987-65-4321", "555-44-3333"],
            "card": [VALID_CARD, "5500005555555559", "340000000000009"],
            "count_widgets": [3, 7, 2],
        }
    )

def _by_col(signals: list[PiiSignal]) -> dict[str, PiiSignal]:
    return {s.column: s for s in signals}

# --------------------------------------------------------------------------- #
# Luhn
# --------------------------------------------------------------------------- #
def test_luhn_accepts_valid():
    assert luhn_check(VALID_CARD) is True
    assert luhn_check("4111 1111 1111 1111") is True

def test_luhn_rejects_invalid():
    assert luhn_check(INVALID_CARD) is False
    assert luhn_check("1234567890123456") is False
    assert luhn_check("123") is False  # too short

# --------------------------------------------------------------------------- #
# Scanner
# --------------------------------------------------------------------------- #
def test_scanner_flags_kinds_and_severities(pii_df):
    signals = _by_col(scan_dataframe(pii_df))

    assert signals["email"].kind == "email"
    assert signals["email"].severity == "high"

    assert signals["ssn"].kind == "ssn"
    assert signals["ssn"].severity == "critical"

    assert signals["card"].kind == "credit_card"
    assert signals["card"].severity == "critical"

    assert signals["phone"].kind == "phone"
    assert signals["phone"].severity == "high"

    assert signals["full_name"].kind == "name"
    assert signals["full_name"].severity == "medium"

    # plain count column should not be flagged as PII
    assert "count_widgets" not in signals

def test_scanner_confidence_in_range(pii_df):
    for s in scan_dataframe(pii_df):
        assert 0.0 <= s.confidence <= 1.0
        assert s.evidence

def test_scanner_value_confirmation_beats_name_only():
    # value-confirmed email should score higher than a bare name-only signal
    df = pd.DataFrame(
        {
            "email": ["x@y.com", "z@w.com"],
            "last_name": ["Doe", "Roe"],
        }
    )
    sig = _by_col(scan_dataframe(df))
    assert sig["email"].confidence > sig["last_name"].confidence

def test_scanner_entropy_identifier():
    df = pd.DataFrame({"token_blob": [f"id-{i:06d}-xyz" for i in range(20)]})
    sig = _by_col(scan_dataframe(df))
    assert "token_blob" in sig
    assert sig["token_blob"].kind == "identifier"

# --------------------------------------------------------------------------- #
# Masking
# --------------------------------------------------------------------------- #
def test_redact():
    out = redact(pd.Series(["secret", "data", None]))
    assert out.tolist()[:2] == ["***", "***"]
    assert pd.isna(out.tolist()[2])

def test_hash_token_deterministic():
    s = pd.Series(["alice", "bob"])
    a = hash_token(s, salt="pepper")
    b = hash_token(s, salt="pepper")
    assert a.tolist() == b.tolist()
    assert all(len(v) == 64 for v in a)
    # different salt -> different token
    c = hash_token(s, salt="other")
    assert c.tolist() != a.tolist()

def test_bucket_numeric():
    out = bucket_numeric(pd.Series([0, 5, 10, 50, 100]), bins=5)
    assert all(isinstance(v, str) and v.startswith("[") for v in out)
    # determinism
    assert out.tolist() == bucket_numeric(pd.Series([0, 5, 10, 50, 100]), bins=5).tolist()

def test_truncate_geo():
    out = truncate_geo(pd.Series([40.748817, -73.985428]), precision=2)
    assert out.tolist() == [40.75, -73.99]

def test_partial_mask():
    out = partial_mask(pd.Series(["123456789", "ab"]), keep=4)
    assert out.tolist()[0] == "*****6789"
    assert out.tolist()[1] == "ab"  # shorter than keep -> unchanged

def test_recommend_strategy():
    assert recommend_strategy(PiiSignal("c", "ssn", 0.9, [], "critical")) == "hash_token"
    assert recommend_strategy(PiiSignal("c", "credit_card", 0.9, [], "critical")) == "hash_token"
    assert recommend_strategy(PiiSignal("c", "email", 0.9, [], "high")) == "partial_mask"
    assert recommend_strategy(PiiSignal("c", "geo", 0.5, [], "medium")) == "truncate_geo"
    assert recommend_strategy(PiiSignal("c", "name", 0.5, [], "medium")) == "redact"

# --------------------------------------------------------------------------- #
# DMBOK scoring
# --------------------------------------------------------------------------- #
def test_dmbok_six_dimensions_in_range(pii_df):
    report = score_dataframe(pii_df)
    names = {d.dimension for d in report.dimensions}
    assert names == {
        "completeness", "validity", "uniqueness",
        "consistency", "timeliness", "accuracy",
    }
    assert len(report.dimensions) == 6
    for d in report.dimensions:
        assert 0.0 <= d.score <= 100.0
    assert 0.0 <= report.overall <= 100.0

def test_dmbok_perfect_completeness():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    report = score_dataframe(df)
    comp = next(d for d in report.dimensions if d.dimension == "completeness")
    assert comp.score == 100.0

def test_dmbok_nulls_lower_completeness():
    df = pd.DataFrame({"a": [1, None, 3], "b": [None, None, "z"]})
    report = score_dataframe(df)
    comp = next(d for d in report.dimensions if d.dimension == "completeness")
    assert comp.score < 100.0

def test_dmbok_uniqueness_with_duplicates():
    df = pd.DataFrame({"id": [1, 1, 2, 3], "v": ["a", "a", "b", "c"]})
    report = score_dataframe(df, key_columns=["id"])
    uniq = next(d for d in report.dimensions if d.dimension == "uniqueness")
    assert uniq.score < 100.0

def test_dmbok_timeliness_recent_vs_old():
    recent = pd.DataFrame({"d": ["2026-05-01", "2026-05-20"]})
    old = pd.DataFrame({"d": ["2010-01-01", "2011-01-01"]})
    r_recent = score_dataframe(recent, date_column="d")
    r_old = score_dataframe(old, date_column="d")
    t_recent = next(d for d in r_recent.dimensions if d.dimension == "timeliness")
    t_old = next(d for d in r_old.dimensions if d.dimension == "timeliness")
    assert t_recent.score > t_old.score

def test_dmbok_consistency_negative_counts():
    df = pd.DataFrame({"count_items": [1, -5, 3, -2]})
    report = score_dataframe(df)
    cons = next(d for d in report.dimensions if d.dimension == "consistency")
    assert cons.score < 100.0
