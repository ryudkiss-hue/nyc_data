"""Tests for app/utils/cache_manager.py — write/read, TTL, stale fallback, eviction."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "inspection_id": ["NYC-001", "NYC-002", "NYC-003"],
            "borough": ["MANHATTAN", "BROOKLYN", "QUEENS"],
            "condition_score": [85, 62, 90],
            "address": ["123 Broadway", "456 Atlantic Ave", "789 Northern Blvd"],
        }
    )


@pytest.fixture()
def cache_manager(tmp_path: Path):
    """Return the cache_manager module with CACHE_DIR redirected to tmp_path."""
    import app.utils.cache_manager as cm

    original_cache_dir = cm.CACHE_DIR
    original_manifest_path = cm._MANIFEST_PATH

    cm.CACHE_DIR = tmp_path
    cm._MANIFEST_PATH = tmp_path / "manifest.json"

    yield cm

    cm.CACHE_DIR = original_cache_dir
    cm._MANIFEST_PATH = original_manifest_path


# ---------------------------------------------------------------------------
# Write and read
# ---------------------------------------------------------------------------


class TestWriteAndReadCache:
    def test_write_and_read_cache(self, cache_manager, sample_df):
        key = "inspection"
        cache_manager.write_cache(key, sample_df)
        result = cache_manager.read_cache(key)
        assert result is not None
        assert list(result.columns) == list(sample_df.columns)
        assert len(result) == len(sample_df)

    def test_write_returns_path(self, cache_manager, sample_df):
        path = cache_manager.write_cache("test_key", sample_df)
        assert isinstance(path, Path)
        assert path.exists()

    def test_read_nonexistent_key_returns_none(self, cache_manager):
        result = cache_manager.read_cache("nonexistent_key_xyz")
        assert result is None

    def test_write_updates_manifest(self, cache_manager, sample_df):
        cache_manager.write_cache("inspection", sample_df)
        manifest = cache_manager.cache_manifest()
        assert "inspection" in manifest
        assert manifest["inspection"]["rows"] == len(sample_df)


# ---------------------------------------------------------------------------
# TTL expiry
# ---------------------------------------------------------------------------


class TestTTLExpiry:
    def test_ttl_expiry_returns_none(self, cache_manager, sample_df):
        """Write cache with TTL=0 (expired immediately), read back → None."""
        key = "violations"
        cache_manager.write_cache(key, sample_df)

        # Manually expire the manifest entry by back-dating expires_at
        manifest = cache_manager.cache_manifest()
        manifest[key]["expires_at"] = "2000-01-01T00:00:00+00:00"
        cache_manager._save_manifest(manifest)

        result = cache_manager.read_cache(key)
        assert result is None

    def test_fresh_cache_returns_data(self, cache_manager, sample_df):
        """Cache written with default TTL should be readable immediately."""
        key = "street_permits"
        cache_manager.write_cache(key, sample_df)
        result = cache_manager.read_cache(key)
        assert result is not None


# ---------------------------------------------------------------------------
# Stale fallback
# ---------------------------------------------------------------------------


class TestStaleFallback:
    def test_stale_fallback_returns_stale_data(self, cache_manager, sample_df):
        """Even expired cache should be returned by read_stale_cache."""
        key = "complaints_311"
        cache_manager.write_cache(key, sample_df)

        # Expire it
        manifest = cache_manager.cache_manifest()
        manifest[key]["expires_at"] = "2000-01-01T00:00:00+00:00"
        cache_manager._save_manifest(manifest)

        # read_cache returns None (expired)
        assert cache_manager.read_cache(key) is None

        # read_stale_cache should return the stale data
        stale = cache_manager.read_stale_cache(key)
        assert stale is not None
        assert len(stale) == len(sample_df)

    def test_stale_fallback_no_data_returns_none(self, cache_manager):
        result = cache_manager.read_stale_cache("no_such_dataset")
        assert result is None


# ---------------------------------------------------------------------------
# Eviction
# ---------------------------------------------------------------------------


class TestEviction:
    def test_eviction_removes_oldest_files(self, cache_manager, sample_df):
        """Evict with max_bytes=1 should remove files until total < 1 byte."""
        cache_manager.write_cache("ds1", sample_df)
        time.sleep(0.01)  # ensure different mtimes
        cache_manager.write_cache("ds2", sample_df)
        time.sleep(0.01)
        cache_manager.write_cache("ds3", sample_df)

        files_before = list(cache_manager.CACHE_DIR.glob("*.parquet.gz"))
        assert len(files_before) >= 2

        # Force eviction of almost everything (1 byte max)
        freed = cache_manager.evict_old_cache(max_bytes=1)
        assert freed > 0

        files_after = list(cache_manager.CACHE_DIR.glob("*.parquet.gz"))
        assert len(files_after) < len(files_before)

    def test_eviction_no_op_when_below_limit(self, cache_manager, sample_df):
        cache_manager.write_cache("small_ds", sample_df)
        freed = cache_manager.evict_old_cache(max_bytes=10 * 1024 * 1024)  # 10 MB
        assert freed == 0


# ---------------------------------------------------------------------------
# last_fetched_iso
# ---------------------------------------------------------------------------


class TestLastFetchedIso:
    def test_returns_iso_string(self, cache_manager, sample_df):
        cache_manager.write_cache("mappluto", sample_df)
        ts = cache_manager.last_fetched_iso("mappluto")
        assert ts is not None
        # Should parse as ISO datetime
        dt = datetime.fromisoformat(ts)
        assert isinstance(dt, datetime)

    def test_returns_none_for_missing_key(self, cache_manager):
        assert cache_manager.last_fetched_iso("not_cached") is None


# ---------------------------------------------------------------------------
# cache_manifest
# ---------------------------------------------------------------------------


class TestCacheManifest:
    def test_cache_manifest_returns_dict(self, cache_manager):
        result = cache_manager.cache_manifest()
        assert isinstance(result, dict)

    def test_cache_manifest_empty_when_no_writes(self, cache_manager):
        result = cache_manager.cache_manifest()
        assert result == {}

    def test_cache_manifest_contains_written_keys(self, cache_manager, sample_df):
        cache_manager.write_cache("inspection", sample_df)
        cache_manager.write_cache("violations", sample_df)
        manifest = cache_manager.cache_manifest()
        assert "inspection" in manifest
        assert "violations" in manifest

    def test_manifest_entry_has_expected_keys(self, cache_manager, sample_df):
        cache_manager.write_cache("inspection", sample_df)
        entry = cache_manager.cache_manifest()["inspection"]
        for field in ("path", "rows", "fetched_at", "expires_at", "ttl_hours"):
            assert field in entry, f"Missing field '{field}' in manifest entry"
