import os

import pytest
import redis
import redis.asyncio as aioredis

from caching import reset_redis_config, setup_redis_config
from caching.backends.redis import RedisBackend


def get_redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture(scope="function")
def sync_redis_client():
    """Create a sync Redis client for testing."""
    try:
        client = redis.from_url(get_redis_url())
        client.ping()  # Test connection
        yield client
        client.close()
    except redis.ConnectionError:
        pytest.skip("Redis server not available")


@pytest.fixture(scope="function")
def async_redis_client():
    """Create an async Redis client for testing."""
    try:
        client = aioredis.from_url(get_redis_url())
        yield client
    except Exception:
        pytest.skip("Redis server not available")


@pytest.fixture(autouse=True)
def reset_config():
    """Reset Redis config before each test."""
    reset_redis_config()
    yield
    reset_redis_config()


@pytest.fixture(autouse=True)
def clear_redis_keys(sync_redis_client):
    """Clear all test cache keys before and after each test."""
    yield
    # Clean up any cache keys created during test
    for key in sync_redis_client.scan_iter("cache:*"):
        sync_redis_client.delete(key)


@pytest.fixture
def setup_sync_redis(sync_redis_client):
    """Setup Redis config with sync client only."""
    setup_redis_config(sync_client=sync_redis_client, key_prefix="cache")
    return sync_redis_client


@pytest.fixture
def setup_async_redis(async_redis_client):
    """Setup Redis config with async client only."""
    setup_redis_config(async_client=async_redis_client, key_prefix="cache")
    return async_redis_client


@pytest.fixture
def setup_both_redis(sync_redis_client, async_redis_client):
    """Setup Redis config with both sync and async clients."""
    setup_redis_config(
        sync_client=sync_redis_client,
        async_client=async_redis_client,
        key_prefix="cache",
    )
    return sync_redis_client, async_redis_client
