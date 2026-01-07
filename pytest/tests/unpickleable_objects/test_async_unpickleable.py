import asyncio

import pytest
from cachify.memory_cache import cache
from cachify.storage.memory_storage import MemoryStorage

TTL = 0.1


class TestUnpickleableArguments:
    """Tests for async caching behavior with lambda arguments (unpickleable)."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        MemoryStorage.clear()

    @pytest.mark.asyncio
    async def test_lambda_argument_caches_successfully(self):
        """Memory cache should handle lambda arguments without raising."""
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(func) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        my_lambda = lambda x: x  # noqa: E731
        result1 = await cached_func(my_lambda)
        result2 = await cached_func(my_lambda)
        result3 = await cached_func(my_lambda)

        assert result1 == result2 == result3
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_different_lambdas__code_produce_same_cache_keys(self):
        """Different lambda objects with the same code should produce the same cache keys."""
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(func) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        result1 = await cached_func(lambda x: x)
        result2 = await cached_func(lambda y: y)

        assert result1 == result2
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_different_lambdas_different_code_produce_different_cache_keys(self):
        """Different lambda objects with the different code should produce different cache keys."""
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(func) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        result1 = await cached_func(lambda x: x)
        result2 = await cached_func(lambda y: y + 1)

        assert result1 != result2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_list_containing_lambda(self):
        """Memory cache should handle lists containing lambdas."""
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(items: list) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        my_lambda = lambda x: x  # noqa: E731
        result1 = await cached_func([1, 2, my_lambda])
        result2 = await cached_func([1, 2, my_lambda])

        assert result1 == result2
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_dict_containing_lock(self):
        """Memory cache should handle dicts containing locks."""
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(data: dict) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        lock = asyncio.Lock()
        result1 = await cached_func({"lock": lock, "value": 42})
        result2 = await cached_func({"lock": lock, "value": 42})

        assert result1 == result2
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_set_containing_hashable_unpickleable_objects(self):
        """Memory cache should handle sets with hashable but unpickleable items."""
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(items: list) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        class UnpickleableHashable:
            def __reduce__(self):
                raise TypeError("Cannot pickle")

        obj1 = UnpickleableHashable()
        obj2 = UnpickleableHashable()

        result1 = await cached_func([obj1, obj2])
        result2 = await cached_func([obj1, obj2])

        assert result1 == result2
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_deeply_nested_unpickleable_objects(self):
        """Memory cache should handle deeply nested structures with unpickleable objects."""
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(data: dict) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        nested_data = {"level1": {"level2": {"level3": [lambda x: x, 1, 2]}}}
        result1 = await cached_func(nested_data)
        result2 = await cached_func(nested_data)

        assert result1 == result2
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_mixed_nested_structures_with_unpickleable(self):
        """Memory cache should handle mixed list/dict/set nesting with unpickleable."""
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(data: dict) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        mixed_data = {
            "list": [1, {"inner_dict": [asyncio.Lock(), 2, 3]}, 4],
            "tuple": (5, (6, {"deep": asyncio.Lock()})),
            "simple": "value",
        }

        result1 = await cached_func(mixed_data)
        result2 = await cached_func(mixed_data)

        assert result1 == result2
        assert call_count == 1


class TestDuplicateObjectReferences:
    """Tests for cycle detection and duplicate object handling in async context."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        MemoryStorage.clear()

    @pytest.mark.asyncio
    async def test_same_object_referenced_multiple_times(self):
        """Cache should handle same unpickleable object referenced multiple times."""
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(items: list) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        lock = asyncio.Lock()
        result1 = await cached_func([lock, lock, lock])
        result2 = await cached_func([lock, lock, lock])

        assert result1 == result2
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_same_object_referenced_different_times(self):
        """Cache should handle same unpickleable object referenced multiple times."""
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(items: list) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        lock = asyncio.Lock()
        result1 = await cached_func([lock, lock])
        result2 = await cached_func([lock, lock, lock])

        assert result1 != result2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_circular_reference_in_dict(self):
        """Cache should handle circular references in data structures."""
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(data: dict) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        circular_dict = {"value": 1, "self": None}
        circular_dict["self"] = circular_dict

        result1 = await cached_func(circular_dict)
        result2 = await cached_func(circular_dict)

        assert result1 == result2
        assert call_count == 1


class TestCacheKeyFuncWithUnpickleable:
    """Tests for cache_key_func returning unpickleable values in async context."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        MemoryStorage.clear()

    @pytest.mark.asyncio
    async def test_cache_key_func_returning_lambda(self):
        """Memory cache should handle cache_key_func returning unpickleable value."""
        call_count = 0
        key_lambda = lambda x: x  # noqa: E731

        @cache(ttl=TTL, cache_key_func=lambda args, kwargs: key_lambda)
        async def cached_func(value: int) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        result1 = await cached_func(1)
        result2 = await cached_func(2)

        assert result1 == result2
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cache_key_func_with_unpickleable_in_tuple(self):
        """Memory cache should handle cache_key_func returning tuple with unpickleable."""
        call_count = 0
        lock = asyncio.Lock()

        @cache(ttl=TTL, cache_key_func=lambda args, kwargs: (args[0], lock))
        async def cached_func(value: int) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        result1 = await cached_func(1)
        result2 = await cached_func(1)
        result3 = await cached_func(2)

        assert result1 == result2
        assert result1 != result3
        assert call_count == 2
