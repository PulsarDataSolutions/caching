import threading
import pytest
import redis

from cachify import redis_cache


class TestUnpickleableArgumentsRaiseError:
    """Tests that unpickleable arguments raise clear errors with Redis cache."""

    def test_lambda_argument_raises_value_error(self, setup_sync_redis: redis.Redis):
        """Redis cache should raise ValueError for lambda arguments."""

        @redis_cache(ttl=60)
        def cached_func(func) -> int:
            return 1

        with pytest.raises(ValueError):
            cached_func(lambda x: x * 2)

    def test_lock_argument_raises_value_error(self, setup_sync_redis: redis.Redis):
        """Redis cache should raise ValueError for Lock arguments."""

        @redis_cache(ttl=60)
        def cached_func(lock: threading.Lock) -> int:
            return 1

        with pytest.raises(ValueError):
            cached_func(threading.Lock())

    def test_nested_unpickleable_raises_value_error(self, setup_sync_redis: redis.Redis):
        """Redis cache should raise ValueError for nested unpickleable objects."""

        @redis_cache(ttl=60)
        def cached_func(data: dict) -> int:
            return 1

        with pytest.raises(ValueError):
            cached_func({"nested": {"lambda": lambda: None}})

    def test_deeply_nested_unpickleable_raises_value_error(self, setup_sync_redis: redis.Redis):
        """Redis cache should raise ValueError for deeply nested unpickleable objects."""

        @redis_cache(ttl=60)
        def cached_func(data: dict) -> int:
            return 1

        with pytest.raises(ValueError):
            cached_func({"level1": {"level2": {"level3": [lambda: None, 1, 2]}}})

    def test_mixed_nested_structures_with_unpickleable_raises(self, setup_sync_redis: redis.Redis):
        """Redis cache should raise ValueError for mixed nested structures with unpickleable."""

        @redis_cache(ttl=60)
        def cached_func(data: dict) -> int:
            return 1

        mixed_data = {
            "list": [1, {"inner_dict": [threading.Lock(), 2, 3]}, 4],
            "tuple": (5, (6, {"deep": threading.Lock()})),
            "simple": "value",
        }

        with pytest.raises(ValueError):
            cached_func(mixed_data)


class TestCacheKeyFuncUnpickleableRaisesError:
    """Tests that cache_key_func returning unpickleable raises clear errors."""

    def test_cache_key_func_returning_lambda_raises(self, setup_sync_redis: redis.Redis):
        """Redis cache should raise ValueError when cache_key_func returns unpickleable."""
        key_lambda = lambda x: x  # noqa: E731

        @redis_cache(ttl=60, cache_key_func=lambda args, kwargs: key_lambda)
        def cached_func(value: int) -> int:
            return value

        with pytest.raises(ValueError):
            cached_func(1)

    def test_cache_key_func_with_unpickleable_in_tuple_raises(self, setup_sync_redis: redis.Redis):
        """Redis cache should raise ValueError when cache_key_func returns tuple with unpickleable."""
        lock = threading.Lock()

        @redis_cache(ttl=60, cache_key_func=lambda args, kwargs: (args[0], lock))
        def cached_func(value: int) -> int:
            return value

        with pytest.raises(ValueError):
            cached_func(1)


class TestIgnoreFieldsWithUnpickleable:
    """Tests that ignore_fields can be used to work around unpickleable arguments."""

    def test_ignore_unpickleable_field_allows_caching(self, setup_sync_redis: redis.Redis):
        """Redis cache should work when unpickleable field is ignored."""
        call_count = 0

        @redis_cache(ttl=60, ignore_fields=("callback",))
        def cached_func(value: int, callback) -> int:
            nonlocal call_count
            call_count += 1
            return value * 2

        my_lambda = lambda x: x  # noqa: E731
        result1 = cached_func(5, callback=my_lambda)
        result2 = cached_func(5, callback=my_lambda)

        assert result1 == result2 == 10
        assert call_count == 1

    def test_ignore_lock_field_allows_caching(self, setup_sync_redis: redis.Redis):
        """Redis cache should work when lock field is ignored."""
        call_count = 0

        @redis_cache(ttl=60, ignore_fields=("lock",))
        def cached_func(value: int, lock: threading.Lock) -> int:
            nonlocal call_count
            call_count += 1
            return value * 2

        lock = threading.Lock()
        result1 = cached_func(5, lock=lock)
        result2 = cached_func(5, lock=lock)

        assert result1 == result2 == 10
        assert call_count == 1
