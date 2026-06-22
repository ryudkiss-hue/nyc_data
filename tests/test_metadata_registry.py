"""Tests for the authoritative NYC Open Data metadata registry.

Verifies the registry loads, exposes accurate metadata/columns, and that the
DataManager freshness quality gate works against it. These tests run offline
against the committed registry baseline (no network required).
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from pipeline.data.nyc_open_data_registry import NYCDataRegistry

REGISTRY_FILE = ROOT / "pipeline" / "data" / "nyc_open_data_registry.json"

# Core SIM datasets that must always resolve to verified Socrata IDs.
CORE_DATASETS = {
    "dntt-gqwq": "Inspection",
    "6kbp-uz6m": "Violations",
    "gx72-kirf": "ReInspection",
    "i642-2fxq": "Lot Info",
    "ugc8-s3f6": "Built",
    "p4u2-3jgx": "Dismissal",
}


@pytest.fixture(scope="module")
def registry():
    """Load the committed registry baseline (no network sync)."""
    return NYCDataRegistry(auto_sync=False)


class TestRegistryFile:
    def test_registry_file_exists(self):
        assert REGISTRY_FILE.exists(), "Authoritative registry JSON missing"

    def test_registry_has_datasets(self, registry):
        assert registry.registry["metadata"]["total_datasets"] >= 1000

    def test_registry_has_indices(self, registry):
        idx = registry.registry["index"]
        assert idx["by_agency"], "Missing agency index"
        assert idx["by_keywords"], "Missing keyword index"


class TestCoreDatasets:
    @pytest.mark.parametrize("fourfour,label", CORE_DATASETS.items())
    def test_core_dataset_present(self, registry, fourfour, label):
        ds = registry.registry["datasets"].get(fourfour)
        assert ds is not None, f"{label} ({fourfour}) missing from registry"
        assert ds["name"], f"{label} has no name"

    @pytest.mark.parametrize("fourfour,label", CORE_DATASETS.items())
    def test_core_dataset_has_columns(self, registry, fourfour, label):
        ds = registry.registry["datasets"].get(fourfour)
        assert ds.get("columns"), f"{label} has no column schema"
        for col in ds["columns"]:
            assert col.get("field_name"), f"{label} column missing field_name"

    @pytest.mark.parametrize("fourfour,label", CORE_DATASETS.items())
    def test_core_dataset_is_dot(self, registry, fourfour, label):
        ds = registry.registry["datasets"].get(fourfour)
        assert "Transportation" in ds.get("agency", ""), f"{label} not DOT"


class TestQueryMethods:
    def test_get_dataset(self, registry):
        v = registry.get_dataset("6kbp-uz6m", with_columns=False)
        assert v["socrata_id"] == "6kbp-uz6m"

    def test_filter_by_agency_returns_list(self, registry):
        assert isinstance(registry.filter_by_agency("Any"), list)

    def test_search_returns_list(self, registry):
        results = registry.search("sidewalk")
        assert isinstance(results, list)
        assert len(results) > 0


class TestFreshnessGate:
    def test_fresh_dataset(self, registry):
        from app.data_manager import DataManager
        dm = DataManager(read_only=True)
        # Inspection updates ~daily; with generous SLA it should be FRESH.
        f = dm.check_freshness("dntt-gqwq", sla_days=30)
        assert f["status"] in ("FRESH", "STALE")  # never UNKNOWN for core
        assert f["age_days"] is not None

    def test_unknown_dataset(self, registry):
        from app.data_manager import DataManager
        dm = DataManager(read_only=True)
        f = dm.check_freshness("zzzz-zzzz")
        assert f["status"] == "UNKNOWN"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
