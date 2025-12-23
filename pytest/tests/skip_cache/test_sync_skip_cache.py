import time
from itertools import count
from typing_extensions import Unpack

from caching.memory_cache import cache
from caching.types import CacheKwargs

TTL = 0.1


def test_skip_cache_bypasses_getting_from_cache():
    counter = count()

    @cache(ttl=TTL)
    def cached_function(**_: Unpack[CacheKwargs]):
        return next(counter)

    result1 = cached_function()
    result2 = cached_function()
    assert result1 == result2, "Normal call should return cached value"

    result3 = cached_function(skip_cache=True)
    assert result3 == result1 + 1, "skip_cache=True should execute function and return new value"

    result4 = cached_function()
    assert result4 == result3, "After skip_cache, normal call should return the value set by skip_cache"


def test_skip_cache_with_function_arguments():
    counter = count()

    @cache(ttl=TTL)
    def cached_function(arg: str, **_: Unpack[CacheKwargs]) -> str:
        return f"{arg}_{next(counter)}"

    result1 = cached_function("test")

    result2 = cached_function("test")
    assert result1 == result2, "Same arguments should return cached value"

    result3 = cached_function("test", skip_cache=True)
    assert result3 != result1, "skip_cache should execute function even with same arguments"
    assert result3 == "test_1", "skip_cache should increment counter"

    result4 = cached_function("test")
    assert result4 == result3, "Normal call should return updated cached value"


def test_skip_cache_respects_ttl_for_setting():
    """Test that values set by skip_cache still respect TTL for expiration"""
    counter = count()

    @cache(ttl=TTL)
    def cached_function(**_: Unpack[CacheKwargs]):
        return next(counter)

    result1 = cached_function(skip_cache=True)
    result2 = cached_function()
    assert result1 == result2, "Normal call should get value set by skip_cache"

    time.sleep(TTL + 0.1)  # Wait for TTL to expire

    result3 = cached_function()
    assert result3 == result1 + 1, "After TTL expiration, should execute function and increment counter"
