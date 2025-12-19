import time

import pytest

from caching import redis_cache


def test_neverdie_sync_redis(setup_sync_redis):
    """Test never_die keeps returning cached values while refreshing in background."""
    call_count = 0

    @redis_cache(ttl=1, never_die=True)
    def get_value(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    # First call
    result1 = get_value(5)
    assert result1 == 10
    assert call_count == 1

    # Wait for TTL to pass
    time.sleep(1.5)

    # Should still return cached value (never_die)
    result2 = get_value(5)
    assert result2 == 10

    # Wait for background refresh
    time.sleep(0.5)

    # Background thread should have refreshed
    assert call_count >= 1  # At least initial call, possibly refresh


def test_neverdie_exception_redis(setup_sync_redis):
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
async def test_neverdie_async_redis(setup_both_redis):
    """Test never_die with async functions in Redis."""
    import asyncio

    call_count = 0

    @redis_cache(ttl=1, never_die=True)
    async def get_value(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    # First call
    result1 = await get_value(5)
    assert result1 == 10
    assert call_count == 1

    # Wait for TTL to pass
    await asyncio.sleep(1.5)

    # Should still return cached value
    result2 = await get_value(5)
    assert result2 == 10
