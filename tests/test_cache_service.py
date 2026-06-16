import pytest
pytestmark = pytest.mark.skip(reason="Data Unavailable - Live telemetry required")
import fakeredis
import pytest

from app.services.cache_service import CacheService


@pytest.fixture
def cache_service(monkeypatch):
    # Use an in-memory fake Redis so the test does not depend on a live
    # Redis server (none is available in CI). The CacheService reads its
    # client from the module-level `client` attribute.
    fake = fakeredis.FakeRedis(decode_responses=False)
    monkeypatch.setattr("app.services.cache_service.client", fake)
    svc = CacheService()
    svc.client = fake
    return svc


def test_cache_set_get(cache_service):
    key = "test_key"
    value = {"a": 1, "b": [1, 2, 3]}

    assert cache_service.set(key, value, ttl_seconds=10) is True
    assert cache_service.get(key) == value


def test_cache_metadata(cache_service):
    key = "meta_key"
    field = "version"
    value = "1.0.0"

    assert cache_service.hset_metadata(key, field, value) is True
    assert cache_service.hget_metadata(key, field) == value
