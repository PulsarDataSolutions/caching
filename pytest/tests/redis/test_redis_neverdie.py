import time
import pytest
import redis
import redis.asyncio

from caching import redis_cache


def test_neverdie_sync_redis(setup_sync_redis: redis.Redis):
    """Test never_die keeps returning cached values while refreshing in background."""
    call_count = 0

    @redis_cache(ttl=0.1, never_die=True)
    def get_value(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    # First call
    result1 = get_value(5)
    assert result1 == 10
    assert call_count == 1

    # Wait for multiple TTL cycles to allow background refreshes
    time.sleep(0.5)

    # Should still return cached value (never_die)
    result2 = get_value(5)
    assert result2 == 10

    # Background thread should have refreshed multiple times
    assert call_count > 2, f"Never-die should auto-refresh, counter: {call_count}"


def test_neverdie_exception_redis(setup_sync_redis: redis.Redis):
    """Test never_die continues serving stale data on function exception."""
    call_count = 0
    should_fail = False

    @redis_cache(ttl=1, never_die=True)
    def get_value(x: int) -> int:
        nonlocal call_count
        call_count += 1
        if should_fail:
            raise Exception("Simulated failure")
        return x * 2

    # First call succeeds
    result1 = get_value(5)
    assert result1 == 10
    assert call_count == 1

    # Enable failures
    should_fail = True

    # Wait for refresh attempt
    time.sleep(1.5)

    # Should still return stale cached value
    result2 = get_value(5)
    assert result2 == 10  # Still returns cached result


@pytest.mark.asyncio
async def test_neverdie_async_redis(
    setup_both_redis: tuple[redis.Redis, redis.asyncio.Redis],
):
    """Test never_die with async functions in Redis."""
    import asyncio

    call_count = 0

    @redis_cache(ttl=0.1, never_die=True)
    async def get_value(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    # First call
    result1 = await get_value(5)
    assert result1 == 10
    assert call_count == 1

    # Wait for multiple TTL cycles to allow background refreshes
    await asyncio.sleep(0.5)

    # Should still return cached value (never_die)
    result2 = await get_value(5)
    assert result2 == 10

    # Background thread should have refreshed multiple times
    assert call_count > 2, f"Never-die should auto-refresh, counter: {call_count}"


@pytest.mark.asyncio
async def test_neverdie_async_exception_redis(
    setup_both_redis: tuple[redis.Redis, redis.asyncio.Redis],
):
    """Test never_die continues serving stale data on async function exception."""
    import asyncio

    call_count = 0
    should_fail = False

    @redis_cache(ttl=1, never_die=True)
    async def get_value(x: int) -> int:
        nonlocal call_count
        call_count += 1
        if should_fail:
            raise Exception("Simulated failure")
        return x * 2

    # First call succeeds
    result1 = await get_value(5)
    assert result1 == 10
    assert call_count == 1

    # Enable failures
    should_fail = True

    # Wait for refresh attempt
    await asyncio.sleep(1.5)

    # Should still return stale cached value
    result2 = await get_value(5)
    assert result2 == 10  # Still returns cached result
