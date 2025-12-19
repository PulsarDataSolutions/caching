import asyncio
import time

import pytest

from caching import redis_cache


@pytest.mark.asyncio
async def test_basic_async_redis_caching(setup_async_redis):
    """Test that async function results are cached in Redis."""
    call_count = 0

    @redis_cache(ttl=60)
    async def get_value(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    # First call should execute function
    result1 = await get_value(5)
    assert result1 == 10
    assert call_count == 1

    # Second call should return cached result
    result2 = await get_value(5)
    assert result2 == 10
    assert call_count == 1  # Function not called again


@pytest.mark.asyncio
async def test_cache_expiration_async_redis(setup_async_redis):
    """Test that cached values expire after TTL (async)."""
    call_count = 0

    @redis_cache(ttl=1)  # 1 second TTL
    async def get_value(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    # First call
    result1 = await get_value(5)
    assert result1 == 10
    assert call_count == 1

    # Wait for expiration
    await asyncio.sleep(1.5)

    # Should call function again after expiration
    result2 = await get_value(5)
    assert result2 == 10
    assert call_count == 2


@pytest.mark.asyncio
async def test_concurrent_access_redis(setup_async_redis):
    """Test concurrent access to same cached value."""
    call_count = 0

    @redis_cache(ttl=60)
    async def slow_function(x: int) -> int:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.2)
        return x * 2

    # Run multiple concurrent calls
    results = await asyncio.gather(
        slow_function(5),
        slow_function(5),
        slow_function(5),
    )

    assert all(r == 10 for r in results)
    # With distributed locking, only one should execute
    assert call_count == 1


@pytest.mark.asyncio
async def test_different_arguments_async_redis(setup_async_redis):
    """Test that different arguments create different cache entries (async)."""
    call_count = 0

    @redis_cache(ttl=60)
    async def get_value(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    result1 = await get_value(5)
    assert result1 == 10
    assert call_count == 1

    result2 = await get_value(10)
    assert result2 == 20
    assert call_count == 2

    # Calling with same args should use cache
    result3 = await get_value(5)
    assert result3 == 10
    assert call_count == 2


@pytest.mark.asyncio
async def test_skip_cache_async_redis(setup_async_redis):
    """Test skip_cache parameter bypasses cache read (async)."""
    call_count = 0

    @redis_cache(ttl=60)
    async def get_value(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    # First call
    result1 = await get_value(5)
    assert result1 == 10
    assert call_count == 1

    # Skip cache should call function again
    result2 = await get_value(5, skip_cache=True)
    assert result2 == 10
    assert call_count == 2


@pytest.mark.asyncio
async def test_separate_cache_keys_async_redis(setup_async_redis):
    """Test that different async functions have separate cache keys."""
    count_a = 0
    count_b = 0

    @redis_cache(ttl=60)
    async def func_a(x: int) -> str:
        nonlocal count_a
        count_a += 1
        return f"a:{x}"

    @redis_cache(ttl=60)
    async def func_b(x: int) -> str:
        nonlocal count_b
        count_b += 1
        return f"b:{x}"

    assert await func_a(1) == "a:1"
    assert await func_b(1) == "b:1"
    assert count_a == 1
    assert count_b == 1

    # Each function should use its own cache
    assert await func_a(1) == "a:1"
    assert await func_b(1) == "b:1"
    assert count_a == 1
    assert count_b == 1


@pytest.mark.asyncio
async def test_complex_objects_async_redis(setup_async_redis):
    """Test caching complex objects in Redis (async)."""

    @redis_cache(ttl=60)
    async def get_data() -> dict:
        return {"key": "value", "nested": {"a": 1, "b": [1, 2, 3]}}

    result1 = await get_data()
    result2 = await get_data()

    assert result1 == result2
    assert result1 == {"key": "value", "nested": {"a": 1, "b": [1, 2, 3]}}
