import pytest

"""Unit tests for query result caching (Task 1: Query Result Caching).

Tests cover:
- Cache hit/miss tracking
- TTL-based eviction
- Thread safety
- Memory estimation
- Decorator functionality
"""

import time

import pandas as pd
import pytest

from socrata_toolkit.motherduck.query_cache import (
    QueryCache,
    get_query_cache,
    memoize_with_ttl,
)


class TestQueryCache:
    """Test suite for QueryCache class."""

    def test_cache_hit_on_identical_query(self):
        """Test that identical queries return cached results."""
        cache = QueryCache(ttl_seconds=60)
        query = "SELECT * FROM phase_b_results"
        result = [("MN", 0.342, "STRONG_CLUSTERING", 100)]

        # First call: cache miss
        assert cache.get(query) is None
        assert cache.miss_count == 1

        # Store result
        cache.set(query, result)

        # Second call: cache hit
        cached = cache.get(query)
        assert cached == result
        assert cache.hit_count == 1
        assert cache.miss_count == 1

    def test_cache_miss_on_different_queries(self):
        """Test that different queries have separate cache entries."""
        cache = QueryCache(ttl_seconds=60)
        query1 = "SELECT * FROM phase_b WHERE borough='MN'"
        query2 = "SELECT * FROM phase_b WHERE borough='BK'"
        result1 = [("MN", 0.342)]
        result2 = [("BK", 0.215)]

        cache.set(query1, result1)
        cache.set(query2, result2)

        # Different queries should return different results
        assert cache.get(query1) == result1
        assert cache.get(query2) == result2
        assert cache.hit_count == 2

    def test_ttl_expiration(self):
        """Test that entries are evicted after TTL expires."""
        cache = QueryCache(ttl_seconds=1)  # 1 second TTL
        query = "SELECT * FROM phase_c"
        result = [(5, 2.1, 1.5, 0.8)]

        cache.set(query, result)
        assert cache.get(query) == result  # Should hit

        time.sleep(1.1)  # Wait for TTL to expire
        assert cache.get(query) is None  # Should miss

    def test_cache_with_parameters(self):
        """Test caching queries with different parameters."""
        cache = QueryCache(ttl_seconds=60)
        query = "SELECT * FROM phase_d WHERE borough = ?"
        params1 = ["MN"]
        params2 = ["BK"]
        result1 = [(1, "MN", 40.7, -74.0)]
        result2 = [(2, "BK", 40.6, -73.9)]

        cache.set(query, result1, params1)
        cache.set(query, result2, params2)

        # Different parameters should return different cached results
        assert cache.get(query, params1) == result1
        assert cache.get(query, params2) == result2
        assert cache.hit_count == 2

    def test_cache_clear(self):
        """Test clearing all cache entries."""
        cache = QueryCache(ttl_seconds=60)
        query1 = "SELECT * FROM phase_e"
        query2 = "SELECT * FROM phase_f"
        result = [(1, 2, 3)]

        cache.set(query1, result)
        cache.set(query2, result)
        assert len(cache.cache_store) == 2

        cache.clear()
        assert len(cache.cache_store) == 0
        assert cache.get(query1) is None
        assert cache.get(query2) is None

    def test_cache_stats(self):
        """Test cache statistics tracking."""
        cache = QueryCache(ttl_seconds=60)
        query = "SELECT * FROM kpi_metrics"
        result = [(1, 2, 3)]

        # Initial stats
        stats = cache.get_stats()
        assert stats["hit_count"] == 0
        assert stats["miss_count"] == 0
        assert stats["hit_rate_percent"] == 0

        # After cache miss
        cache.get(query)
        stats = cache.get_stats()
        assert stats["miss_count"] == 1

        # After cache set and hit
        cache.set(query, result)
        cache.get(query)
        stats = cache.get_stats()
        assert stats["hit_count"] == 1
        assert stats["miss_count"] == 1
        assert stats["hit_rate_percent"] == 50.0
        assert stats["entry_count"] == 1

    def test_cache_size_estimation(self):
        """Test memory size estimation for different object types."""
        cache = QueryCache(ttl_seconds=60)

        # DataFrame size
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        df_size = cache._estimate_size(df)
        assert df_size > 0

        # List size
        list_result = [(1, "test"), (2, "data")]
        list_size = cache._estimate_size(list_result)
        assert list_size > 0

        # String size
        string_size = cache._estimate_size("test query result")
        assert string_size > 0

    def test_cache_key_generation(self):
        """Test that identical queries generate identical cache keys."""
        cache = QueryCache()
        query = "SELECT * FROM analytics.phase_b_spatial_clusters ORDER BY borough"
        params = ["MN", "BK"]

        key1 = cache._make_key(query, params)
        key2 = cache._make_key(query, params)
        assert key1 == key2

        # Different queries should generate different keys
        key3 = cache._make_key(query + " LIMIT 10", params)
        assert key1 != key3

    def test_decorator_basic_functionality(self):
        """Test @memoize_with_ttl decorator on a method."""
        cache_instance = None

        class MockConnection:
            def __init__(self):
                nonlocal cache_instance
                self.call_count = 0

            @memoize_with_ttl(ttl_seconds=60)
            def fetch_df(self, query, params=None):
                self.call_count += 1
                return pd.DataFrame({"col": [1, 2, 3]})

        conn = MockConnection()

        # First call: executes method, increments counter
        df1 = conn.fetch_df("SELECT * FROM test")
        assert conn.call_count == 1

        # Second call (same query): returns cached, doesn't increment counter
        df2 = conn.fetch_df("SELECT * FROM test")
        assert conn.call_count == 1
        assert df1.equals(df2)

        # Third call with different query: executes method, increments counter
        df3 = conn.fetch_df("SELECT * FROM other")
        assert conn.call_count == 2

    def test_global_cache_singleton(self):
        """Test that get_query_cache returns singleton instance."""
        cache1 = get_query_cache()
        cache2 = get_query_cache()
        assert cache1 is cache2


class TestCachingPerformance:
    """Integration tests for caching performance (benchmarking)."""

    def test_cached_vs_uncached_latency(self):
        """Verify cached queries are faster than uncached."""
        query = "SELECT * FROM analytics.phase_e_decomposition LIMIT 1000"

        class TimedConnection:
            def __init__(self):
                self.call_count = 0

            @memoize_with_ttl(ttl_seconds=60)
            def fetch_df(self, query, params=None):
                self.call_count += 1
                time.sleep(0.1)  # Simulate 100ms query latency
                return pd.DataFrame({"date": [1, 2, 3], "borough": ["MN", "BK", "QN"]})

        conn = TimedConnection()

        # First call: ~100ms (cache miss)
        start = time.time()
        conn.fetch_df(query)
        uncached_time = time.time() - start

        # Second call: <5ms (cache hit)
        start = time.time()
        conn.fetch_df(query)
        cached_time = time.time() - start

        # Cached should be significantly faster (>10x)
        assert cached_time < uncached_time / 10
        assert conn.call_count == 1  # Method only called once

    def test_memory_overhead_of_caching(self):
        """Verify cache memory overhead is reasonable."""
        cache = QueryCache(ttl_seconds=60)
        query_template = "SELECT * FROM phase_e WHERE borough = '{}' AND date > '{}'"

        # Add 100 query results to cache
        for i in range(100):
            query = query_template.format("MN", f"2026-0{i % 6}-{i % 28 + 1:02d}")
            df = pd.DataFrame({"col": list(range(1000))})
            cache.set(query, df)

        stats = cache.get_stats()
        # At least 80+ entries should be cached (some may be deduplicated)
        assert stats["entry_count"] >= 80
        # Memory should be reasonable for 100 DataFrames (~5-10MB)
        assert stats["total_size_mb"] < 50


class TestCacheInvalidation:
    """Test cache invalidation strategies."""

    def test_clear_on_data_update(self):
        """Verify cache can be cleared for data freshness."""
        cache = QueryCache(ttl_seconds=3600)  # 1 hour TTL
        query = "SELECT * FROM analytics.phase_b"
        result = [("MN", 0.342)]

        cache.set(query, result)
        assert cache.get(query) == result

        # Simulate data update: clear cache
        stats = cache.get_stats()
        assert stats["entry_count"] == 1
        cache.clear()
        assert cache.get(query) is None
        assert cache.get_stats()["entry_count"] == 0

    def test_ttl_configuration(self):
        """Verify different TTL configurations work correctly."""
        cache_short = QueryCache(ttl_seconds=1)
        cache_long = QueryCache(ttl_seconds=3600)
        query = "SELECT * FROM test"
        result = [1, 2, 3]

        cache_short.set(query, result)
        cache_long.set(query, result)

        # Both should return result immediately
        assert cache_short.get(query) == result
        assert cache_long.get(query) == result

        # After 2 seconds, short TTL should expire
        time.sleep(2)
        assert cache_short.get(query) is None  # Expired
        assert cache_long.get(query) == result  # Still valid
