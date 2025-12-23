import asyncio
import pytest
import redis.asyncio

from caching import redis_cache


@pytest.mark.asyncio
async def test_basic_async_redis_caching(setup_async_redis: redis.asyncio.Redis):
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
async def test_cache_expiration_async_redis(setup_async_redis: redis.asyncio.Redis):
    """Test that cached values expire after TTL (async)."""
    call_count = 0

    @redis_cache(ttl=1)
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
async def test_concurrent_access_redis(setup_async_redis: redis.asyncio.Redis):
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
async def test_different_arguments_async_redis(setup_async_redis: redis.asyncio.Redis):
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
async def test_skip_cache_async_redis(setup_async_redis: redis.asyncio.Redis):
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

    # Normal call should still use cache
    result3 = await get_value(5)
    assert result3 == 10
    assert call_count == 2


@pytest.mark.asyncio
async def test_separate_cache_keys_async_redis(setup_async_redis: redis.asyncio.Redis):
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
async def test_complex_objects_async_redis(setup_async_redis: redis.asyncio.Redis):
    """Test caching complex objects in Redis (async)."""
    call_count = 0

    @redis_cache(ttl=60)
    async def get_data() -> dict:
        nonlocal call_count
        call_count += 1
        return {"key": "value", "nested": {"a": 1, "b": [1, 2, 3]}}

    result1 = await get_data()
    result2 = await get_data()

    assert result1 == result2
    assert result1 == {"key": "value", "nested": {"a": 1, "b": [1, 2, 3]}}
    assert call_count == 1  # Verify caching actually happened


@pytest.mark.asyncio
async def test_cache_key_func_async_redis(setup_async_redis: redis.asyncio.Redis):
    """Test custom cache key function with Redis (async)."""

    @redis_cache(ttl=60, cache_key_func=lambda args, kwargs: args[0])
    async def get_value(x: int, y: int) -> int:
        return x + y

    # Same x, different y should return cached result (because cache_key only uses x)
    result1 = await get_value(5, 10)
    assert result1 == 15

    result2 = await get_value(5, 20)
    assert result2 == 15  # Cached based on x=5


@pytest.mark.asyncio
async def test_ignore_fields_async_redis(setup_async_redis: redis.asyncio.Redis):
    """Test ignore_fields parameter with Redis (async)."""
    call_count = 0

    @redis_cache(ttl=60, ignore_fields=("ignored",))
    async def get_value(x: int, ignored: str) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    result1 = await get_value(5, ignored="a")
    assert result1 == 10
    assert call_count == 1

    # Different ignored value should still use cache
    result2 = await get_value(5, ignored="b")
    assert result2 == 10
    assert call_count == 1


@pytest.mark.asyncio
async def test_cache_key_func_and_ignore_fields_mutual_exclusion_async_redis():
    """Test that providing both cache_key_func and ignore_fields raises ValueError (async)."""
    with pytest.raises(ValueError, match="Either cache_key_func or ignore_fields"):

        @redis_cache(ttl=60, cache_key_func=lambda args, kwargs: args[0], ignore_fields=("b",))
        async def func(a: int, b: int) -> int:
            return a + b
