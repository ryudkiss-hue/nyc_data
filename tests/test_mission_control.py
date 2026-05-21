"""Mission Control analytics smoke tests (no live Socrata)."""

from __future__ import annotations

import pandas as pd

from app import analytics, data_loader


def test_dataset_registry_covers_required_endpoints():
    # Prompt lists 15 groups; registry includes all named fourfours (16 layers).
    assert len(data_loader.DATASET_REGISTRY) >= 15


def test_normalize_bbl():
    s = pd.Series(["3022330001", "302233-0001"])
    out = data_loader.normalize_bbl(s)
    assert out.iloc[0] == "3022330001"


def test_qa_qc_ledger_owner_mismatch():
    lot = pd.DataFrame({"bbl": ["1000010001"], "owner": ["City"]})
    lot["_bbl"] = data_loader.normalize_bbl(lot["bbl"])
    pluto = pd.DataFrame({"bbl": ["1000010001"], "ownername": ["Private"]})
    pluto["_bbl"] = data_loader.normalize_bbl(pluto["bbl"])
    ledger, stale, joins = analytics.qa_qc_inventory_ledger(lot, pluto, pd.DataFrame())
    assert joins >= 1
    assert ledger["owner_discrepancy"].any()


def test_productivity_roi_math():
    roi = analytics.compute_productivity_roi(
        lots_validated=10,
        spatial_conflicts_checked=4,
        contracts_cleared=6,
        joins_automated=3,
        actionable_discrepancies=5,
    )
    assert roi.hours_reclaimed == (10 * 3 + 4 * 15 + 6 * 5) / 60.0


def test_run_all_workflows_empty_frames():
    frames = {k: pd.DataFrame() for k in data_loader.DATASET_REGISTRY}
    out = analytics.run_all_workflows(frames)
    assert "roi" in out
    assert out["roi"].joins_automated >= 0
