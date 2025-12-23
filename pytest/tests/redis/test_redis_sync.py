import time
import pytest
import redis

from caching import redis_cache


def test_basic_sync_redis_caching(setup_sync_redis: redis.Redis):
    """Test that sync function results are cached in Redis."""
    call_count = 0

    @redis_cache(ttl=60)
    def get_value(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    # First call should execute function
    result1 = get_value(5)
    assert result1 == 10
    assert call_count == 1

    # Second call should return cached result
    result2 = get_value(5)
    assert result2 == 10
    assert call_count == 1  # Function not called again


def test_cache_expiration_redis(setup_sync_redis: redis.Redis):
    """Test that cached values expire after TTL."""
    call_count = 0

    @redis_cache(ttl=1)
    def get_value(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    # First call
    result1 = get_value(5)
    assert result1 == 10
    assert call_count == 1

    # Wait for expiration
    time.sleep(1.5)

    # Should call function again after expiration
    result2 = get_value(5)
    assert result2 == 10
    assert call_count == 2


def test_different_arguments_redis(setup_sync_redis: redis.Redis):
    """Test that different arguments create different cache entries."""
    call_count = 0

    @redis_cache(ttl=60)
    def get_value(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    result1 = get_value(5)
    assert result1 == 10
    assert call_count == 1

    result2 = get_value(10)
    assert result2 == 20
    assert call_count == 2

    # Calling with same args should use cache
    result3 = get_value(5)
    assert result3 == 10
    assert call_count == 2


def test_skip_cache_redis(setup_sync_redis: redis.Redis):
    """Test skip_cache parameter bypasses cache read."""
    call_count = 0

    @redis_cache(ttl=60)
    def get_value(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    # First call
    result1 = get_value(5)
    assert result1 == 10
    assert call_count == 1

    # Skip cache should call function again
    result2 = get_value(5, skip_cache=True)
    assert result2 == 10
    assert call_count == 2

    # Normal call should still use cache
    result3 = get_value(5)
    assert result3 == 10
    assert call_count == 2


def test_separate_cache_keys_redis(setup_sync_redis: redis.Redis):
    """Test that different functions have separate cache keys."""
    count_a = 0
    count_b = 0

    @redis_cache(ttl=60)
    def func_a(x: int) -> str:
        nonlocal count_a
        count_a += 1
        return f"a:{x}"

    @redis_cache(ttl=60)
    def func_b(x: int) -> str:
        nonlocal count_b
        count_b += 1
        return f"b:{x}"

    assert func_a(1) == "a:1"
    assert func_b(1) == "b:1"
    assert count_a == 1
    assert count_b == 1

    # Each function should use its own cache
    assert func_a(1) == "a:1"
    assert func_b(1) == "b:1"
    assert count_a == 1
    assert count_b == 1


def test_cache_key_func_redis(setup_sync_redis: redis.Redis):
    """Test custom cache key function with Redis."""

    @redis_cache(ttl=60, cache_key_func=lambda args, kwargs: args[0])
    def get_value(x: int, y: int) -> int:
        return x + y

    # Same x, different y should return cached result (because cache_key only uses x)
    result1 = get_value(5, 10)
    assert result1 == 15

    result2 = get_value(5, 20)
    assert result2 == 15  # Cached based on x=5


def test_ignore_fields_redis(setup_sync_redis: redis.Redis):
    """Test ignore_fields parameter with Redis."""
    call_count = 0

    @redis_cache(ttl=60, ignore_fields=("ignored",))
    def get_value(x: int, ignored: str) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    result1 = get_value(5, ignored="a")
    assert result1 == 10
    assert call_count == 1

    # Different ignored value should still use cache
    result2 = get_value(5, ignored="b")
    assert result2 == 10
    assert call_count == 1


def test_complex_objects_redis(setup_sync_redis: redis.Redis):
    """Test caching complex objects in Redis."""
    call_count = 0

    @redis_cache(ttl=60)
    def get_data() -> dict:
        nonlocal call_count
        call_count += 1
        return {"key": "value", "nested": {"a": 1, "b": [1, 2, 3]}}

    result1 = get_data()
    result2 = get_data()

    assert result1 == result2
    assert result1 == {"key": "value", "nested": {"a": 1, "b": [1, 2, 3]}}
    assert call_count == 1  # Verify caching actually happened


def test_cache_key_func_and_ignore_fields_mutual_exclusion_redis():
    """Test that providing both cache_key_func and ignore_fields raises ValueError."""
    with pytest.raises(ValueError, match="Either cache_key_func or ignore_fields"):

        @redis_cache(ttl=60, cache_key_func=lambda args, kwargs: args[0], ignore_fields=("b",))
        def func(a: int, b: int) -> int:
            return a + b
