import inspect
from typing import Callable

from caching._async import async_decorator
from caching._sync import sync_decorator
from caching.backends.redis import RedisBackend
from caching.backends.redis_lock import RedisLockManager
from caching.types import CacheKeyFunction, F, Number


def redis_cache(
    ttl: Number = 300,
    never_die: bool = False,
    cache_key_func: CacheKeyFunction | None = None,
    ignore_fields: tuple[str, ...] = (),
) -> Callable[[F], F]:
    """
    A decorator that caches function results in Redis based on function id and arguments.
    Only allows one entry to the main function, making subsequent calls with the same arguments
    wait for the first call to complete and use its cached result.

    Requires setup_redis_config() to be called before use.

    Args:
        ttl: Time to live for cached items in seconds, defaults to 5 minutes
        never_die: If True, the cache will never expire and will be recalculated based on the ttl
        cache_key_func: custom cache key function, used for more complex cache scenarios
        ignore_fields: tuple of strings with the function params that we want to ignore when creating the cache key

    Features:
        - Works for both sync and async functions
        - Only allows one execution at a time per function+args (distributed locking)
        - Makes subsequent calls wait for the first call to complete
        - Uses Redis for distributed caching across multiple processes/machines
    """
    from caching.features.never_die import register_never_die_function_redis

    if cache_key_func and ignore_fields:
        raise Exception("Either cache_key_func or ignore_fields can be provided, but not both")

    def decorator(function: F) -> F:
        if not inspect.iscoroutinefunction(function):
            return sync_decorator(
                function,
                ttl,
                never_die,
                cache_key_func,
                ignore_fields,
                backend=RedisBackend,
                lock_context=RedisLockManager.sync_lock,
                register_never_die=register_never_die_function_redis,
            )

        return async_decorator(
            function,
            ttl,
            never_die,
            cache_key_func,
            ignore_fields,
            backend=RedisBackend,
            lock_context=RedisLockManager.async_lock,
            register_never_die=register_never_die_function_redis,
        )

    return decorator
