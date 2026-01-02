import pytest
from collections.abc import Callable

from caching.storage.memory_storage import MemoryStorage
from caching.memory_cache import cache

TTL = 0.1


class TestDictArguments:
    """Tests for caching behavior with dict arguments (async)."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        MemoryStorage.clear()

    @pytest.mark.asyncio
    async def test_same_dict_returns_cached_result(self):
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(data: dict) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        result1 = await cached_func({"a": 1, "b": 2})
        result2 = await cached_func({"a": 1, "b": 2})

        assert result1 == result2
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_dict_with_different_insertion_order_produces_different_cache(self):
        """
        Dicts with same content but different insertion order produce DIFFERENT cache keys.

        This is because pickle (used for cache key generation) preserves dict insertion order.
        This is a known limitation - if you need order-independent dict caching,
        use a custom cache_key_func that sorts dict keys.
        """
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(data: dict) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        dict1 = {"a": 1, "b": 2, "c": 3}
        dict2 = {"c": 3, "a": 1, "b": 2}

        result1 = await cached_func(dict1)
        result2 = await cached_func(dict2)

        # Different insertion order = different cache keys (pickle preserves order)
        assert result1 != result2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_different_dict_values_produce_different_cache(self):
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(data: dict) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        result1 = await cached_func({"a": 1})
        result2 = await cached_func({"a": 2})

        assert result1 != result2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_nested_dict_same_order_caching(self):
        """Nested dicts with same structure and order should hit same cache."""
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(data: dict) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        nested1 = {"outer": {"inner": 1, "other": 2}}
        nested2 = {"outer": {"inner": 1, "other": 2}}

        result1 = await cached_func(nested1)
        result2 = await cached_func(nested2)

        assert result1 == result2
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_nested_dict_different_order_produces_different_cache(self):
        """
        Nested dicts with different key order produce DIFFERENT cache keys.

        This is because pickle preserves dict insertion order at all nesting levels.
        """
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(data: dict) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        nested1 = {"outer": {"inner": 1, "other": 2}}
        nested2 = {"outer": {"other": 2, "inner": 1}}

        result1 = await cached_func(nested1)
        result2 = await cached_func(nested2)

        # Different nested key order = different cache keys
        assert result1 != result2
        assert call_count == 2


class TestListArguments:
    """Tests for caching behavior with list arguments (async)."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        MemoryStorage.clear()

    @pytest.mark.asyncio
    async def test_same_list_returns_cached_result(self):
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(items: list) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        result1 = await cached_func([1, 2, 3])
        result2 = await cached_func([1, 2, 3])

        assert result1 == result2
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_list_order_matters(self):
        """Lists with same elements but different order should produce different cache keys."""
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(items: list) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        result1 = await cached_func([1, 2, 3])
        result2 = await cached_func([3, 2, 1])

        # List order matters, so these should be different cache entries
        assert result1 != result2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_different_list_produces_different_cache(self):
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(items: list) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        result1 = await cached_func([1, 2])
        result2 = await cached_func([1, 2, 3])

        assert result1 != result2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_nested_list_caching(self):
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(items: list) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        nested1 = [[1, 2], [3, 4]]
        nested2 = [[1, 2], [3, 4]]

        result1 = await cached_func(nested1)
        result2 = await cached_func(nested2)

        assert result1 == result2
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_list_with_mixed_types(self):
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(items: list) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        mixed1 = [1, "two", 3.0, None, True]
        mixed2 = [1, "two", 3.0, None, True]

        result1 = await cached_func(mixed1)
        result2 = await cached_func(mixed2)

        assert result1 == result2
        assert call_count == 1


class TestSetArguments:
    """Tests for caching behavior with set arguments (async)."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        MemoryStorage.clear()

    @pytest.mark.asyncio
    async def test_same_set_returns_cached_result(self):
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(items: set) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        result1 = await cached_func({1, 2, 3})
        result2 = await cached_func({1, 2, 3})

        assert result1 == result2
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_set_order_does_not_matter(self):
        """Sets with same elements should produce same cache key regardless of creation order."""
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(items: set) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        # Creating sets in different ways but with same elements
        set1 = {1, 2, 3}
        set2 = {3, 2, 1}

        result1 = await cached_func(set1)
        result2 = await cached_func(set2)

        # Sets are unordered, so these should hit the same cache
        assert result1 == result2
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_different_set_produces_different_cache(self):
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(items: set) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        result1 = await cached_func({1, 2})
        result2 = await cached_func({1, 2, 3})

        assert result1 != result2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_frozenset_caching(self):
        """Frozensets should also work as cache keys."""
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(items: frozenset) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        result1 = await cached_func(frozenset({1, 2, 3}))
        result2 = await cached_func(frozenset({3, 2, 1}))

        assert result1 == result2
        assert call_count == 1


class TestMixedMutableArguments:
    """Tests for caching behavior with multiple mutable arguments (async)."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        MemoryStorage.clear()

    @pytest.mark.asyncio
    async def test_multiple_mutable_args(self):
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(data: dict, items: list, unique: set) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        result1 = await cached_func({"a": 1}, [1, 2], {3, 4})
        result2 = await cached_func({"a": 1}, [1, 2], {3, 4})

        assert result1 == result2
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_kwargs_with_mutable_types(self):
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(data: dict | None = None, items: list | None = None) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        result1 = await cached_func(data={"a": 1}, items=[1, 2])
        result2 = await cached_func(items=[1, 2], data={"a": 1})

        # Same kwargs but in different order should hit same cache
        assert result1 == result2
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_positional_vs_keyword_args(self):
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(data: dict, items: list) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        result1 = await cached_func({"a": 1}, [1, 2])
        result2 = await cached_func(data={"a": 1}, items=[1, 2])

        # Same values passed as positional vs keyword should hit same cache
        assert result1 == result2
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_dict_containing_list_same_order(self):
        """Dict containing lists with same key order should hit same cache."""
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(data: dict) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        complex1 = {"list": [1, 2, 3], "tuple": (4, 5, 6)}
        complex2 = {"list": [1, 2, 3], "tuple": (4, 5, 6)}

        result1 = await cached_func(complex1)
        result2 = await cached_func(complex2)

        assert result1 == result2
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_dict_different_key_order_produces_different_cache(self):
        """
        Dict with different key order produces DIFFERENT cache keys,
        even if the values are the same.
        """
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(data: dict) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        complex1 = {"list": [1, 2, 3], "tuple": (4, 5, 6)}
        complex2 = {"tuple": (4, 5, 6), "list": [1, 2, 3]}

        result1 = await cached_func(complex1)
        result2 = await cached_func(complex2)

        # Different key order = different cache keys
        assert result1 != result2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_list_containing_dicts(self):
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(items: list) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        list1 = [{"a": 1}, {"b": 2}]
        list2 = [{"a": 1}, {"b": 2}]

        result1 = await cached_func(list1)
        result2 = await cached_func(list2)

        assert result1 == result2
        assert call_count == 1


class TestMutationAfterCaching:
    """Tests to ensure mutations after caching don't affect cache behavior (async)."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        MemoryStorage.clear()

    @pytest.mark.asyncio
    async def test_mutating_dict_after_cache_does_not_affect_cache(self):
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(data: dict) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        original = {"a": 1}
        result1 = await cached_func(original)

        # Mutate the dict after caching
        original["b"] = 2

        # Call with original value (now mutated)
        result2 = await cached_func({"a": 1})

        # Should still hit cache with {"a": 1}
        assert result1 == result2
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_mutating_list_after_cache_does_not_affect_cache(self):
        call_count = 0

        @cache(ttl=TTL)
        async def cached_func(items: list) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        original = [1, 2]
        result1 = await cached_func(original)

        # Mutate the list after caching
        original.append(3)

        # Call with original value (before mutation)
        result2 = await cached_func([1, 2])

        # Should still hit cache with [1, 2]
        assert result1 == result2
        assert call_count == 1
