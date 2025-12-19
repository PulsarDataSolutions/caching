import functools
import inspect
from typing import Any, Callable, ContextManager, cast

from caching._sync.lock import _SYNC_LOCKS
from caching.bucket import CacheBucket, MemoryBackend
from caching.types import CacheBackend, CacheKeyFunction, F, Number
from caching.utils.functions import get_function_id


def sync_decorator(
    function: F,
    ttl: Number,
    never_die: bool = False,
    cache_key_func: CacheKeyFunction | None = None,
    ignore_fields: tuple[str, ...] = (),
    backend: type[CacheBackend] | None = None,
    lock_context: Callable[[str, str], ContextManager] | None = None,
    register_never_die: Callable[..., None] | None = None,
) -> F:
    """
    Sync decorator implementation.

    Args:
        function: The function to wrap
        ttl: Time to live in seconds
        never_die: If True, cache never expires and refreshes in background
        cache_key_func: Custom cache key function
        ignore_fields: Fields to ignore when creating cache key
        backend: Cache backend class (defaults to MemoryBackend)
        lock_context: Lock context manager factory (defaults to memory locks)
        register_never_die: Function to register never_die entries (defaults to memory implementation)
    """
    if backend is None:
        backend = MemoryBackend

    if lock_context is None:

        def lock_context(fid: str, ckey: str) -> ContextManager:
            return _SYNC_LOCKS[fid][ckey]

    if register_never_die is None:
        from caching.features.never_die import register_never_die_function

        register_never_die = register_never_die_function

    function_id = get_function_id(function)
    function_signature = inspect.signature(function)  # to map args→param names

    @functools.wraps(function)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        skip_cache = kwargs.pop("skip_cache", False)
        cache_key = CacheBucket.create_cache_key(function_signature, cache_key_func, ignore_fields, args, kwargs)

        if never_die:
            register_never_die(function, ttl, args, kwargs, cache_key_func, ignore_fields, backend)

        if cache_entry := backend.get(function_id, cache_key, skip_cache):
            return cache_entry.result

        with lock_context(function_id, cache_key):
            if cache_entry := backend.get(function_id, cache_key, skip_cache):
                return cache_entry.result

            result = function(*args, **kwargs)
            backend.set(function_id, cache_key, result, None if never_die else ttl)
            return result

    return cast(F, sync_wrapper)
