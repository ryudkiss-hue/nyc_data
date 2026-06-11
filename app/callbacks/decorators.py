"""
Callback decorators for performance monitoring and caching.
"""

import functools
import time
import logging
from typing import Any, Callable, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ============================================================================
# CACHING DECORATOR
# ============================================================================

_CACHE_STORE = {}

def memoize_with_ttl(seconds: int = 600):
    """
    Cache decorator with TTL (time-to-live) in seconds.

    Args:
        seconds: Cache duration in seconds (default: 10 minutes)

    Example:
        @memoize_with_ttl(seconds=300)
        def expensive_computation(data):
            return process(data)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Create cache key from function name + args
            cache_key = f"{func.__name__}_{args}_{kwargs}"

            # Check if cached and not expired
            if cache_key in _CACHE_STORE:
                value, expiry = _CACHE_STORE[cache_key]
                if datetime.now() < expiry:
                    logger.debug(f"Cache hit: {func.__name__}")
                    return value

            # Compute and cache
            result = func(*args, **kwargs)
            _CACHE_STORE[cache_key] = (result, datetime.now() + timedelta(seconds=seconds))
            logger.debug(f"Cache miss: {func.__name__}")
            return result

        return wrapper
    return decorator

# ============================================================================
# TIMING DECORATOR
# ============================================================================

def timer_callback(func: Callable) -> Callable:
    """
    Measure callback execution time and log performance metrics.

    Example:
        @timer_callback
        @memoize_with_ttl(seconds=300)
        def update_chart(filters):
            return compute_figure(filters)
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start

            # Log performance
            if elapsed > 0.5:
                logger.warning(f"{func.__name__} took {elapsed:.3f}s (>500ms threshold)")
            else:
                logger.info(f"{func.__name__} completed in {elapsed:.3f}s")

            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"{func.__name__} failed after {elapsed:.3f}s: {str(e)}")
            raise

    return wrapper

# ============================================================================
# CACHE MANAGEMENT
# ============================================================================

def clear_cache():
    """Clear all cached values."""
    global _CACHE_STORE
    _CACHE_STORE.clear()
    logger.info("Cache cleared")

def get_cache_stats() -> dict:
    """Get cache statistics."""
    now = datetime.now()
    active = sum(1 for _, (_, expiry) in _CACHE_STORE.items() if expiry > now)
    return {
        'total_keys': len(_CACHE_STORE),
        'active_keys': active,
        'expired_keys': len(_CACHE_STORE) - active
    }
