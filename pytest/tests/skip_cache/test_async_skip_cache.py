import pytest
import asyncio
from itertools import count
from typing_extensions import Unpack

from caching.memory_cache import cache
from caching.types import CacheKwargs

TTL = 0.1


@pytest.mark.asyncio
async def test_skip_cache_bypasses_getting_from_cache():
    counter = count()

    @cache(ttl=TTL)
    async def cached_function(**_: Unpack[CacheKwargs]):
        return next(counter)

    result1 = await cached_function()  # 0
    result2 = await cached_function()  # 0 (from cache)
    assert result1 == result2, "Normal call should return cached value"

    result3 = await cached_function(skip_cache=True)  # 1 (executes function, skips cache get)
    assert result3 == result1 + 1, "skip_cache=True should execute function and return new value"

    result4 = await cached_function()  # 1 (from cache - the value set by skip_cache call)
    assert result4 == result3, "After skip_cache, normal call should return the value set by skip_cache"


@pytest.mark.asyncio
async def test_skip_cache_with_function_arguments():
    counter = count()

    @cache(ttl=TTL)
    async def cached_function(arg: str, **_: Unpack[CacheKwargs]) -> str:
        return f"{arg}_{next(counter)}"

    result1 = await cached_function("test")  # "test_0"

    result2 = await cached_function("test")  # "test_0" (from cache)
    assert result1 == result2, "Same arguments should return cached value"

    result3 = await cached_function("test", skip_cache=True)  # "test_1" (executes, updates cache)
    assert result3 != result1, "skip_cache should execute function even with same arguments"
    assert result3 == "test_1", "skip_cache should increment counter"

    result4 = await cached_function("test")  # "test_1" (from cache)
    assert result4 == result3, "Normal call should return updated cached value"


@pytest.mark.asyncio
async def test_skip_cache_respects_ttl_for_setting():
    """Test that values set by skip_cache still respect TTL for expiration"""
    counter = count()

    @cache(ttl=TTL)
    async def cached_function(**_: Unpack[CacheKwargs]):
        return next(counter)

    result1 = await cached_function(skip_cache=True)  # 0 (executes, sets cache)
    result2 = await cached_function()  # 0 (from cache)
    assert result1 == result2, "Normal call should get value set by skip_cache"

    await asyncio.sleep(TTL + 0.1)  # Wait for TTL to expire

    result3 = await cached_function()  # 1 (cache expired, executes function)
    assert result3 == result1 + 1, "After TTL expiration, should execute function and increment counter"
