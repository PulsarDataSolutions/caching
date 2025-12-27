import os
import pytest
import pytest_asyncio
import redis
import redis.asyncio as aioredis

from caching import (
    DEFAULT_KEY_PREFIX,
    clear_never_die_registry,
    reset_redis_config,
    setup_redis_config,
)


def get_redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture(scope="function")
def sync_redis_client():
    """Create a sync Redis client for testing."""
    try:
        client = redis.from_url(get_redis_url())
        client.ping()
        yield client
        client.close()
    except redis.ConnectionError:
        pytest.skip("Redis server not available")


@pytest_asyncio.fixture(scope="function")
async def async_redis_client():
    """Create an async Redis client for testing."""
    try:
        client = aioredis.from_url(get_redis_url())
        await client.ping()  # type: ignore
        yield client
        await client.aclose()
    except redis.ConnectionError:
        pytest.skip("Redis server not available")


@pytest.fixture(autouse=True)
def reset_config():
    """Reset Redis config and never_die registry before each test."""
    from caching.redis.lock import _AsyncHeartbeatManager, _SyncHeartbeatManager

    clear_never_die_registry()
    reset_redis_config()
    _AsyncHeartbeatManager.reset()
    _SyncHeartbeatManager.reset()
    yield
    clear_never_die_registry()
    reset_redis_config()
    _AsyncHeartbeatManager.reset()
    _SyncHeartbeatManager.reset()


@pytest.fixture(autouse=True)
def clear_redis_keys(sync_redis_client: redis.Redis):
    """Clear all test cache keys before and after each test."""
    pattern = f"{DEFAULT_KEY_PREFIX}:*"
    # Clean up before test
    for key in sync_redis_client.scan_iter(pattern):
        sync_redis_client.delete(key)
    yield
    # Clean up after test
    for key in sync_redis_client.scan_iter(pattern):
        sync_redis_client.delete(key)


@pytest.fixture
def setup_sync_redis(sync_redis_client: redis.Redis):
    """Setup Redis config with sync client only."""
    setup_redis_config(sync_client=sync_redis_client)
    return sync_redis_client


@pytest.fixture
def setup_async_redis(async_redis_client: aioredis.Redis):
    """Setup Redis config with async client only."""
    setup_redis_config(async_client=async_redis_client)
    return async_redis_client


@pytest.fixture
def setup_both_redis(
    sync_redis_client: redis.Redis,
    async_redis_client: aioredis.Redis,
):
    """Setup Redis config with both sync and async clients."""
    setup_redis_config(
        sync_client=sync_redis_client,
        async_client=async_redis_client,
    )
    return sync_redis_client, async_redis_client
