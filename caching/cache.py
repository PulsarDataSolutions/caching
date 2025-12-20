import inspect
import threading
from typing import Callable

from caching._async import async_decorator
from caching._async.lock import _ASYNC_LOCKS
from caching._sync import sync_decorator
from caching._sync.lock import _SYNC_LOCKS
from caching.bucket import CacheBucket, MemoryBackend
from caching.features.never_die import register_never_die_function
from caching.types import CacheKeyFunction, F, Number

_CACHE_CLEAR_THREAD: threading.Thread | None = None
_CACHE_CLEAR_LOCK: threading.Lock = threading.Lock()


def _start_cache_clear_thread():
    """This is to avoid memory leaks by clearing expired cache items periodically."""
    global _CACHE_CLEAR_THREAD
    with _CACHE_CLEAR_LOCK:
        if _CACHE_CLEAR_THREAD and _CACHE_CLEAR_THREAD.is_alive():
            return
        _CACHE_CLEAR_THREAD = threading.Thread(target=CacheBucket.clear_expired_cached_items, daemon=True)
        _CACHE_CLEAR_THREAD.start()


def cache(
    ttl: Number = 300,
    never_die: bool = False,
    cache_key_func: CacheKeyFunction | None = None,
    ignore_fields: tuple[str, ...] = (),
) -> Callable[[F], F]:
    """
    A decorator that caches function results based on function id and arguments.
    Only allows one entry to the main function, making subsequent calls with the same arguments
    wait for the first call to complete and use its cached result.

    Args:
        ttl: Time to live for cached items in seconds, defaults to 5 minutes
        never_die: If True, the cache will never expire and will be recalculated based on the ttl
        cache_key_func: custom cache key function, used for more complex cache scenarios
        ignore_fields: tuple of strings with the function params that we want to ignore when creating the cache key

    Features:
        - Works for both sync and async functions
        - Only allows one execution at a time per function+args
        - Makes subsequent calls wait for the first call to complete
    """

    if cache_key_func and ignore_fields:
        raise ValueError("Either cache_key_func or ignore_fields can be provided, but not both")

    _start_cache_clear_thread()

    def decorator(function: F) -> F:
        if inspect.iscoroutinefunction(function):
            return async_decorator(
                function=function,
                ttl=ttl,
                never_die=never_die,
                cache_key_func=cache_key_func,
                ignore_fields=ignore_fields,
                backend=MemoryBackend,
                lock_context=lambda fid, ckey: _ASYNC_LOCKS[fid][ckey],
                register_never_die=register_never_die_function,
            )
        return sync_decorator(
            function=function,
            ttl=ttl,
            never_die=never_die,
            cache_key_func=cache_key_func,
            ignore_fields=ignore_fields,
            backend=MemoryBackend,
            lock_context=lambda fid, ckey: _SYNC_LOCKS[fid][ckey],
            register_never_die=register_never_die_function,
        )

    return decorator
