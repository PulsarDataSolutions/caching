import pytest
from collections.abc import Callable

from caching.memory_cache import cache

TTL = 1


@pytest.fixture()
def function_with_cache_using_ignore():

    @cache(ttl=TTL, ignore_fields=("b",))
    def sync_cached_function(a: int, b: int) -> int:
        return a + b

    return sync_cached_function


def test_ignore_arg_param(function_with_cache_using_ignore: Callable[..., int]):
    result1 = function_with_cache_using_ignore(a=1, b=2)
    result2 = function_with_cache_using_ignore(a=1, b=3)

    assert result1 == result2

    result1 = function_with_cache_using_ignore(2, 2)
    result2 = function_with_cache_using_ignore(2, 3)

    assert result1 == result2

    result1 = function_with_cache_using_ignore(b=2, a=3)
    result2 = function_with_cache_using_ignore(a=3, b=5)

    assert result1 == result2
