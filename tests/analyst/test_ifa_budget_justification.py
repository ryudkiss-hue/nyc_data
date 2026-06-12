"""Tests for IFABudgetJustification."""
import pandas as pd
import pytest
from socrata_toolkit.analyst.ifa_budget_justification import (
    IFABudgetJustification,
    BoroughBudgetAllocation,
    COST_PER_RAMP_USD,
)
from socrata_toolkit.engineering.ramp_analysis import BoroughRampStats

SAMPLE_STATS = [
    BoroughRampStats(
        "MN",
        1000,
        800,
        0.80,
        ci_lower=0.77,
        ci_upper=0.83,
        sample_size=1000,
        reliability="high",
    ),
    BoroughRampStats(
        "BX",
        800,
        640,
        0.80,
        ci_lower=0.77,
        ci_upper=0.83,
        sample_size=800,
        reliability="high",
    ),
    BoroughRampStats(
        "BK",
        600,
        420,
        0.70,
        ci_lower=0.66,
        ci_upper=0.74,
        sample_size=600,
        reliability="high",
    ),
]


def test_cost_constant():
    assert COST_PER_RAMP_USD == 45_000


def test_compute_allocations():
    gen = IFABudgetJustification()
    allocations = gen.compute_allocations(SAMPLE_STATS)
    assert len(allocations) == 3
    assert all(isinstance(a, BoroughBudgetAllocation) for a in allocations)
    bk = next(a for a in allocations if a.borough == "BK")
    assert bk.ramps_remaining == 120  # 600 * (0.90 - 0.70)
    assert bk.base_cost_usd == 120 * 45_000


def test_total_budget():
    gen = IFABudgetJustification()
    allocations = gen.compute_allocations(SAMPLE_STATS)
    total = gen.total_budget(allocations)
    assert total > 0
    assert isinstance(total, float)


def test_pdf_bytes_returned(tmp_path):
    gen = IFABudgetJustification()
    allocations = gen.compute_allocations(SAMPLE_STATS)
    out = tmp_path / "test_ifa.pdf"
    gen.export_to_pdf(allocations, str(out))
    assert out.exists()
    assert out.stat().st_size > 0


def test_zero_gap_borough_zero_cost():
    completed = [BoroughRampStats("MN", 100, 95, 0.95, reliability="high", sample_size=100)]
    gen = IFABudgetJustification()
    allocations = gen.compute_allocations(completed)
    assert all(a.ramps_remaining == 0 for a in allocations)
