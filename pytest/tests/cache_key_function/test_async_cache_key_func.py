import pytest
from typing import Any
from collections.abc import Callable, Coroutine

from caching.memory_cache import cache

TTL = 1


@pytest.fixture()
def function_with_cache_key_func_args():

    @cache(ttl=TTL, cache_key_func=lambda args, kwargs: (args[0], args[2]))
    async def async_cached_function(a: int, b: int, c: int) -> int:
        return a + b + c

    return async_cached_function


@pytest.mark.asyncio
async def test_cache_key_func_args(
    function_with_cache_key_func_args: Callable[..., Coroutine[Any, Any, int]],
):
    result1 = await function_with_cache_key_func_args(1, 2, 3)
    result2 = await function_with_cache_key_func_args(1, 5, 3)

    assert result1 == result2


@pytest.fixture()
def function_with_cache_key_func_kwargs():

    @cache(ttl=TTL, cache_key_func=lambda args, kwargs: (kwargs["a"], kwargs["b"]))
    async def async_cached_function(a: int, b: int, c: int) -> int:
        return a + b + c

    return async_cached_function


@pytest.mark.asyncio
async def test_cache_key_func_kwargs(
    function_with_cache_key_func_kwargs: Callable[..., Coroutine[Any, Any, int]],
):
    result1 = await function_with_cache_key_func_kwargs(a=1, b=2, c=3)
    result2 = await function_with_cache_key_func_kwargs(a=1, b=2, c=4)

    assert result1 == result2

    result1 = await function_with_cache_key_func_kwargs(a=2, b=2, c=3)
    result2 = await function_with_cache_key_func_kwargs(c=4, b=2, a=2)

    assert result1 == result2


@pytest.fixture()
def function_with_cache_key_func_args_and_kwargs():

    @cache(ttl=TTL, cache_key_func=lambda args, kwargs: (args[0], kwargs["b"]))
    async def async_cached_function(a: int, b: int, c: int) -> int:
        return a + b + c

    return async_cached_function


@pytest.mark.asyncio
async def test_cache_key_func_args_and_kwargs(
    function_with_cache_key_func_args_and_kwargs: Callable[..., Coroutine[Any, Any, int]],
):
    result1 = await function_with_cache_key_func_args_and_kwargs(1, b=2, c=3)
    result2 = await function_with_cache_key_func_args_and_kwargs(1, b=2, c=4)

    assert result1 == result2

    result1 = await function_with_cache_key_func_args_and_kwargs(2, b=2, c=3)
    result2 = await function_with_cache_key_func_args_and_kwargs(2, c=5, b=2)

    assert result1 == result2
