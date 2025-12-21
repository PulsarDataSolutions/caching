import time
import pytest
import threading
from collections.abc import Callable

from caching.storage.memory_storage import MemoryStorage
from caching.memory_cache import cache

TTL = 0.1


@pytest.fixture()
def function_with_cache():
    MemoryStorage.clear()  # Clear cache before each test
    call_count = 0

    @cache(ttl=TTL)
    def sync_cached_function(arg=None) -> int:
        """Return a unique value on each real function call"""
        nonlocal call_count
        call_count += 1
        return call_count

    return sync_cached_function


def test_basic_sync_caching(function_with_cache: Callable[..., int]):
    result1 = function_with_cache()
    result2 = function_with_cache()

    assert result1 == result2


def test_cache_expiration(function_with_cache: Callable[..., int]):
    result1 = function_with_cache()
    time.sleep(TTL + 0.1)  # wait for cache expiration
    result2 = function_with_cache()

    assert result1 != result2


def test_different_arguments(function_with_cache: Callable[..., int]):
    result1 = function_with_cache()
    result2 = function_with_cache("different")

    assert result1 != result2

    result3 = function_with_cache()

    assert result1 == result3


def test_separate_cache_keys(function_with_cache: Callable[..., int]):
    result1 = function_with_cache("key1")
    result2 = function_with_cache("key2")

    assert result1 != result2

    result1_again = function_with_cache("key1")
    result2_again = function_with_cache("key2")

    assert result1 == result1_again
    assert result2 == result2_again


def test_concurrent_access():
    """Test that concurrent access with locking works correctly."""
    call_count = 0

    @cache(ttl=60)
    def slow_function(arg=None) -> int:
        nonlocal call_count
        call_count += 1
        time.sleep(0.2)
        return call_count

    results = []

    def call_function():
        results.append(slow_function())

    threads = [threading.Thread(target=call_function) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    first_result = results[0]
    assert all(result == first_result for result in results)
    assert call_count == 1  # Only one actual execution


def test_cache_key_func_and_ignore_fields_mutual_exclusion():
    """Test that providing both cache_key_func and ignore_fields raises ValueError."""
    with pytest.raises(ValueError, match="Either cache_key_func or ignore_fields"):

        @cache(ttl=60, cache_key_func=lambda args, kwargs: args[0], ignore_fields=("b",))
        def func(a: int, b: int) -> int:
            return a + b
