import functools
import inspect
from typing import Any, cast

from caching.storage.memory_storage import MemoryStorage
from caching.types import CacheConfig, CacheKeyFunction, F, Number
from caching.utils.functions import get_function_id


def sync_decorator(
    function: F,
    ttl: Number,
    never_die: bool,
    cache_key_func: CacheKeyFunction | None,
    ignore_fields: tuple[str, ...],
    config: CacheConfig,
) -> F:
    function_id = get_function_id(function)
    function_signature = inspect.signature(function)  # to map args→param names

    @functools.wraps(function)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        skip_cache = kwargs.pop("skip_cache", False)
        cache_key = MemoryStorage.create_cache_key(function_signature, cache_key_func, ignore_fields, args, kwargs)

        if never_die:
            config.register_never_die(function, ttl, args, kwargs, cache_key_func, ignore_fields, config.storage)

        if cache_entry := config.storage.get(function_id, cache_key, skip_cache):
            return cache_entry.result

        with config.sync_lock(function_id, cache_key):
            if cache_entry := config.storage.get(function_id, cache_key, skip_cache):
                return cache_entry.result

            result = function(*args, **kwargs)
            config.storage.set(function_id, cache_key, result, None if never_die else ttl)
            return result

    return cast(F, sync_wrapper)
