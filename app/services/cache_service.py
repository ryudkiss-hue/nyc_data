from __future__ import annotations

import logging
import os
from typing import Any

import msgpack
import redis
import zstandard as zstd

logger = logging.getLogger(__name__)

# Redis configuration: Expects REDIS_URL or fallback
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
client = redis.Redis.from_url(redis_url, decode_responses=False)

class CacheService:
    """
    Service for analytical caching with compression and structured storage.
    """

    def __init__(self):
        self.client = client
        self.zstd_compressor = zstd.ZstdCompressor()
        self.zstd_decompressor = zstd.ZstdDecompressor()

    def get(self, key: str) -> Any:
        """Fetch and decompress/deserialize analytical payloads."""
        try:
            data = self.client.get(key)
            if not data:
                return None

            decompressed = self.zstd_decompressor.decompress(data)
            return msgpack.unpackb(decompressed)
        except Exception as e:
            logger.error("Cache fetch failed for %s: %s", key, e)
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Serialize/compress and cache analytical payloads with TTL."""
        try:
            serialized = msgpack.packb(value)
            compressed = self.zstd_compressor.compress(serialized)
            return self.client.set(key, compressed, ex=ttl_seconds)
        except Exception as e:
            logger.error("Cache set failed for %s: %s", key, e)
            return False

    def hset_metadata(self, key: str, field: str, value: Any) -> bool:
        """Store metadata in a hash (uses Redis ziplist optimization)."""
        try:
            # Metadata is stored as serialized strings in a hash field.
            # redis hset returns the number of newly added fields (an int);
            # normalize to a bool to honor the declared return type.
            self.client.hset(key, field, str(value))
            return True

        except Exception as e:
            logger.error("Metadata hset failed for %s:%s: %s", key, field, e)
            return False

    def hget_metadata(self, key: str, field: str) -> str | None:
        """Retrieve metadata from a hash."""
        try:
            result = self.client.hget(key, field)
            return result.decode('utf-8') if result else None
        except Exception as e:
            logger.error("Metadata hget failed for %s:%s: %s", key, field, e)
            return None
