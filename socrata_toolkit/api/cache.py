"""Redis-based caching layer with intelligent invalidation.

Provides caching for KPI summaries, segment details, contractor metrics,
and incident lists. Integrates with Phase 2 metrics for cache hit/miss tracking.

Features:
    - Hierarchical cache keys
    - TTL management per data type
    - Cache invalidation on mutations
    - Graceful degradation if Redis unavailable
    - Cache hit/miss metrics emission
    - Cache warming on startup

Cache Strategies:
    - Summary KPIs: 2 hours (materialized daily by Phase 3)
    - Segment details: 24 hours (static data)
    - Contractor metrics: 6 hours (refreshed weekly by repair_scheduling DAG)
    - Incident lists: 1 hour (updated daily by incident_ingestion DAG)
    - Audit logs: No cache (fresh every query)

Example:
    from socrata_toolkit.api.cache import CacheManager
    cache = CacheManager(redis_url="redis://localhost:6379/0")
    cache.set("kpi:material_metrics:asphalt", {"defect_rate": 12.5}, ttl=3600)
    data = cache.get("kpi:material_metrics:asphalt")
"""

from __future__ import annotations

from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Optional
import json
import logging

logger = logging.getLogger(__name__)

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    logger.warning("redis-py not installed; caching will be disabled")


class CacheManager:
    """Redis cache manager with TTL and invalidation support.

    Handles get/set/delete operations with hierarchical key namespacing
    and graceful degradation if Redis is unavailable.

    Attributes:
        redis_url: Redis connection URL
        default_ttl: Default TTL in seconds (3600)
        redis_client: Redis client instance (None if unavailable)
    """

    def __init__(self, redis_url: str, default_ttl: int = 3600, timeout: float = 5.0):
        """Initialize cache manager.

        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379/0)
            default_ttl: Default TTL in seconds
            timeout: Connection timeout in seconds

        Example:
            >>> cache = CacheManager("redis://localhost:6379/0")
            >>> cache.is_available()
            True
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.timeout = timeout
        self.redis_client: Optional[redis.Redis] = None
        self.available = False

        if HAS_REDIS:
            try:
                self.redis_client = redis.from_url(redis_url, socket_timeout=timeout)
                # Test connection
                self.redis_client.ping()
                self.available = True
                logger.info("Redis cache available")
            except Exception as e:
                logger.warning(f"Redis connection failed, caching disabled: {str(e)}")
                self.redis_client = None

    def is_available(self) -> bool:
        """Check if Redis is available.

        Returns:
            bool: True if cache is operational
        """
        return self.available and self.redis_client is not None

    def get(self, key: str, parse_json: bool = True) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key
            parse_json: Parse JSON strings to dict (default True)

        Returns:
            Cached value or None if not found/unavailable

        Example:
            >>> cache.get("kpi:material_metrics:asphalt")
            {'defect_rate': 12.5, 'hazard_count': 45}
        """
        if not self.is_available():
            return None

        try:
            value = self.redis_client.get(key)
            if value is None:
                return None

            if parse_json:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return value.decode("utf-8") if isinstance(value, bytes) else value
            else:
                return value
        except Exception as e:
            logger.warning(f"Cache get error for {key}: {str(e)}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None, serialize_json: bool = True) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if None)
            serialize_json: Serialize to JSON (default True)

        Returns:
            bool: True if successful

        Example:
            >>> cache.set("kpi:material_metrics:asphalt", {"defect_rate": 12.5}, ttl=3600)
            True
        """
        if not self.is_available():
            return False

        ttl = ttl or self.default_ttl

        try:
            if serialize_json and not isinstance(value, (str, bytes)):
                value = json.dumps(value)

            self.redis_client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.warning(f"Cache set error for {key}: {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key

        Returns:
            bool: True if successful
        """
        if not self.is_available():
            return False

        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for {key}: {str(e)}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "kpi:*" to delete all KPI cache)

        Returns:
            int: Number of keys deleted

        Example:
            >>> cache.delete_pattern("kpi:*")  # Invalidate all KPI cache
            12
        """
        if not self.is_available():
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache delete_pattern error for {pattern}: {str(e)}")
            return 0

    def flush_all(self) -> bool:
        """Flush entire cache (dangerous!).

        Returns:
            bool: True if successful
        """
        if not self.is_available():
            return False

        try:
            self.redis_client.flushdb()
            logger.info("Cache flushed")
            return True
        except Exception as e:
            logger.warning(f"Cache flush error: {str(e)}")
            return False

    def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for key.

        Args:
            key: Cache key

        Returns:
            Remaining TTL in seconds, or None if not found

        Example:
            >>> cache.get_ttl("kpi:material_metrics:asphalt")
            3598  # Expires in 3598 seconds
        """
        if not self.is_available():
            return None

        try:
            ttl = self.redis_client.ttl(key)
            return ttl if ttl >= 0 else None
        except Exception as e:
            logger.warning(f"Cache ttl error for {key}: {str(e)}")
            return None

    def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key.

        Args:
            key: Cache key
            ttl: New TTL in seconds

        Returns:
            bool: True if successful
        """
        if not self.is_available():
            return False

        try:
            self.redis_client.expire(key, ttl)
            return True
        except Exception as e:
            logger.warning(f"Cache expire error for {key}: {str(e)}")
            return False


def cache_key(*args: str) -> str:
    """Generate hierarchical cache key from arguments.

    Args:
        *args: Key components (concatenated with ':')

    Returns:
        str: Hierarchical cache key

    Example:
        >>> cache_key("kpi", "material_metrics", "asphalt")
        'kpi:material_metrics:asphalt'
    """
    return ":".join(str(arg) for arg in args)


def invalidate_cache(pattern: str = "*") -> Callable:
    """Decorator to invalidate cache after mutation.

    Args:
        pattern: Cache key pattern to invalidate (default "*" for all)

    Returns:
        Callable: Decorator function

    Example:
        @invalidate_cache(pattern="kpi:*")
        async def update_kpi(kpi_data):
            # ... update logic
            return updated_data
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, cache_manager: Optional[CacheManager] = None, **kwargs):
            result = await func(*args, **kwargs)

            # Invalidate cache pattern after mutation
            if cache_manager and cache_manager.is_available():
                deleted = cache_manager.delete_pattern(pattern)
                logger.info(f"Cache invalidation: deleted {deleted} keys matching {pattern}")

            return result

        return wrapper

    return decorator


class CacheStats:
    """Track cache hit/miss statistics.

    Attributes:
        hits: Number of cache hits
        misses: Number of cache misses
        sets: Number of cache sets
        errors: Number of cache errors
    """

    def __init__(self):
        """Initialize cache statistics."""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.errors = 0

    def increment_hit(self) -> None:
        """Record cache hit."""
        self.hits += 1

    def increment_miss(self) -> None:
        """Record cache miss."""
        self.misses += 1

    def increment_set(self) -> None:
        """Record cache set."""
        self.sets += 1

    def increment_error(self) -> None:
        """Record cache error."""
        self.errors += 1

    def get_hit_rate(self) -> float:
        """Get cache hit rate (0-1).

        Returns:
            float: Hit rate percentage (0.0 to 1.0)
        """
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    def to_dict(self) -> dict:
        """Convert to dictionary.

        Returns:
            dict: Cache statistics

        Example:
            >>> stats.to_dict()
            {'hits': 150, 'misses': 50, 'hit_rate': 0.75, 'sets': 100, 'errors': 2}
        """
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.get_hit_rate(),
            "sets": self.sets,
            "errors": self.errors,
        }


# Predefined cache key patterns and TTL configurations
class CacheKeys:
    """Standard cache key patterns."""

    # KPI cache keys
    KPI_SUMMARY = cache_key("kpi", "summary")
    KPI_MATERIAL_METRICS = lambda material: cache_key("kpi", "material_metrics", material)
    KPI_ADA_COMPLIANCE = cache_key("kpi", "ada_compliance")
    KPI_HAZARD_COVERAGE = cache_key("kpi", "hazard_coverage")
    KPI_COST_ANALYTICS = cache_key("kpi", "cost_analytics")

    # Segment cache keys
    SEGMENT_DETAIL = lambda segment_id: cache_key("segment", segment_id)
    SEGMENT_INCIDENTS = lambda segment_id: cache_key("segment", segment_id, "incidents")
    SEGMENT_REPAIRS = lambda segment_id: cache_key("segment", segment_id, "repairs")

    # Incident cache keys
    INCIDENT_LIST = cache_key("incidents", "list")
    INCIDENT_DETAIL = lambda incident_id: cache_key("incident", incident_id)

    # Repair cache keys
    REPAIR_LIST = cache_key("repairs", "list")
    REPAIR_DETAIL = lambda repair_id: cache_key("repair", repair_id)

    # Contractor cache keys
    CONTRACTOR_LIST = cache_key("contractors", "list")
    CONTRACTOR_DETAIL = lambda contractor_id: cache_key("contractor", contractor_id)
    CONTRACTOR_PERFORMANCE = lambda contractor_id: cache_key("contractor", contractor_id, "performance")


class CacheTTLs:
    """Standard cache TTLs by data type."""

    SUMMARY_KPIS = 2 * 60 * 60  # 2 hours
    SEGMENT_DETAILS = 24 * 60 * 60  # 24 hours
    CONTRACTOR_METRICS = 6 * 60 * 60  # 6 hours
    INCIDENT_LISTS = 1 * 60 * 60  # 1 hour
    REPAIR_LISTS = 1 * 60 * 60  # 1 hour

    @staticmethod
    def get_ttl_for_type(cache_type: str) -> int:
        """Get TTL for cache type.

        Args:
            cache_type: Type of cache (summary_kpis, segment_details, etc.)

        Returns:
            int: TTL in seconds

        Example:
            >>> CacheTTLs.get_ttl_for_type("summary_kpis")
            7200
        """
        ttl_map = {
            "summary_kpis": CacheTTLs.SUMMARY_KPIS,
            "segment_details": CacheTTLs.SEGMENT_DETAILS,
            "contractor_metrics": CacheTTLs.CONTRACTOR_METRICS,
            "incident_lists": CacheTTLs.INCIDENT_LISTS,
            "repair_lists": CacheTTLs.REPAIR_LISTS,
        }
        return ttl_map.get(cache_type, 3600)  # Default 1 hour
