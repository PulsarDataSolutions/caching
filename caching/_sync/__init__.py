import functools
import inspect
from typing import Any, Callable, ContextManager, cast

from caching.bucket import CacheBucket
from caching.types import CacheBackend, CacheKeyFunction, F, Number
from caching.utils.functions import get_function_id


def sync_decorator(
    function: F,
    ttl: Number,
    never_die: bool,
    cache_key_func: CacheKeyFunction | None,
    ignore_fields: tuple[str, ...],
    backend: CacheBackend,
    lock_context: Callable[[str, str], ContextManager],
    register_never_die: Callable[..., None],
) -> F:
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
