import pytest
from typing import Any
from collections.abc import Callable, Coroutine

from caching.memory_cache import cache

TTL = 1


@pytest.fixture()
def function_with_cache_using_ignore():

    @cache(ttl=TTL, ignore_fields=("b",))
    async def async_cached_function(a: int, b: int) -> int:
        return a + b

    return async_cached_function


@pytest.mark.asyncio
async def test_ignore_arg_param(
    function_with_cache_using_ignore: Callable[..., Coroutine[Any, Any, int]],
):
    result1 = await function_with_cache_using_ignore(a=1, b=2)
    result2 = await function_with_cache_using_ignore(a=1, b=3)

    assert result1 == result2

    result1 = await function_with_cache_using_ignore(2, 2)
    result2 = await function_with_cache_using_ignore(2, 3)

    assert result1 == result2

    result1 = await function_with_cache_using_ignore(b=2, a=3)
    result2 = await function_with_cache_using_ignore(a=3, b=5)

    assert result1 == result2
