import inspect
from typing import Callable

from caching._async import async_decorator
from caching._sync import sync_decorator
from caching.types import CacheConfig, CacheKeyFunction, F, Number


def create_cache_decorator(
    ttl: Number,
    never_die: bool,
    cache_key_func: CacheKeyFunction | None,
    ignore_fields: tuple[str, ...],
    config: CacheConfig,
) -> Callable[[F], F]:
    """
    Create a cache decorator with the given configuration.

    This is a shared factory used by both memory_cache and redis_cache
    to avoid code duplication.
    """
    if cache_key_func and ignore_fields:
        raise ValueError("Either cache_key_func or ignore_fields can be provided, but not both")

    def decorator(function: F) -> F:
        if inspect.iscoroutinefunction(function):
            return async_decorator(
                function=function,
                ttl=ttl,
                never_die=never_die,
                cache_key_func=cache_key_func,
                ignore_fields=ignore_fields,
                config=config,
            )
        return sync_decorator(
            function=function,
            ttl=ttl,
            never_die=never_die,
            cache_key_func=cache_key_func,
            ignore_fields=ignore_fields,
            config=config,
        )

    return decorator
