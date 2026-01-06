import functools
import inspect
from typing import Any, Callable, cast

from cachify.features.never_die import register_never_die_function
from cachify.types import CacheConfig, CacheKeyFunction, F, Number
from cachify.utils.arguments import create_cache_key


def _async_decorator(
    function: F,
    ttl: Number,
    never_die: bool,
    cache_key_func: CacheKeyFunction | None,
    ignore_fields: tuple[str, ...],
    config: CacheConfig,
) -> F:
    @functools.wraps(function)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        skip_cache = kwargs.pop("skip_cache", False)
        cache_key = create_cache_key(function, cache_key_func, ignore_fields, args, kwargs, config.process_isolated)

        if cache_entry := await config.storage.aget(cache_key, skip_cache):
            return cache_entry.result

        async with config.async_lock(cache_key):
            if cache_entry := await config.storage.aget(cache_key, skip_cache):
                return cache_entry.result

            result = await function(*args, **kwargs)
            await config.storage.aset(cache_key, result, None if never_die else ttl)

            if never_die:
                register_never_die_function(function, ttl, args, kwargs, cache_key_func, ignore_fields, config)

            return result

    return cast(F, async_wrapper)


def _sync_decorator(
    function: F,
    ttl: Number,
    never_die: bool,
    cache_key_func: CacheKeyFunction | None,
    ignore_fields: tuple[str, ...],
    config: CacheConfig,
) -> F:
    @functools.wraps(function)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        skip_cache = kwargs.pop("skip_cache", False)
        cache_key = create_cache_key(function, cache_key_func, ignore_fields, args, kwargs, config.process_isolated)

        if cache_entry := config.storage.get(cache_key, skip_cache):
            return cache_entry.result

        with config.sync_lock(cache_key):
            if cache_entry := config.storage.get(cache_key, skip_cache):
                return cache_entry.result

            result = function(*args, **kwargs)
            config.storage.set(cache_key, result, None if never_die else ttl)

            if never_die:
                register_never_die_function(function, ttl, args, kwargs, cache_key_func, ignore_fields, config)

            return result

    return cast(F, sync_wrapper)


def base_cache(
    ttl: Number,
    never_die: bool,
    cache_key_func: CacheKeyFunction | None,
    ignore_fields: tuple[str, ...],
    config: CacheConfig,
) -> Callable[[F], F]:
    """
    Base cache decorator factory used by both memory and Redis cache implementations.

    Args:
        ttl: Time to live for cached items in seconds
        never_die: If True, the cache will never expire and will be recalculated based on the ttl
        cache_key_func: Custom cache key function, used for more complex cache scenarios
        ignore_fields: Tuple of strings with the function params to ignore when creating the cache key
        config: Cache configuration specifying storage, locks, and never_die registration

    Features:
        - Works for both sync and async functions
        - Only allows one execution at a time per function+args
        - Makes subsequent calls wait for the first call to complete
    """
    if cache_key_func and ignore_fields:
        raise ValueError("Either cache_key_func or ignore_fields can be provided, but not both")

    def decorator(function: F) -> F:
        if inspect.iscoroutinefunction(function):
            return _async_decorator(
                function=function,
                ttl=ttl,
                never_die=never_die,
                cache_key_func=cache_key_func,
                ignore_fields=ignore_fields,
                config=config,
            )
        return _sync_decorator(
            function=function,
            ttl=ttl,
            never_die=never_die,
            cache_key_func=cache_key_func,
            ignore_fields=ignore_fields,
            config=config,
        )

    return decorator
