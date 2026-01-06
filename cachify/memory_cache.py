import threading
from typing import Callable

from cachify.cache import base_cache
from cachify.storage.memory_storage import MemoryStorage
from cachify.types import CacheConfig, CacheKeyFunction, F, Number
from cachify.utils.locks import ASYNC_LOCKS, SYNC_LOCKS

_CACHE_CLEAR_THREAD: threading.Thread | None = None
_CACHE_CLEAR_LOCK: threading.Lock = threading.Lock()

_MEMORY_CONFIG = CacheConfig(
    storage=MemoryStorage,
    sync_lock=lambda cache_key: SYNC_LOCKS[cache_key],
    async_lock=lambda cache_key: ASYNC_LOCKS[cache_key],
    process_isolated=True,
)


def _start_cache_clear_thread():
    """This is to avoid memory leaks by clearing expired cache items periodically."""
    global _CACHE_CLEAR_THREAD
    with _CACHE_CLEAR_LOCK:
        if _CACHE_CLEAR_THREAD and _CACHE_CLEAR_THREAD.is_alive():
            return
        _CACHE_CLEAR_THREAD = threading.Thread(target=MemoryStorage.clear_expired_cached_items, daemon=True)
        _CACHE_CLEAR_THREAD.start()


def cache(
    ttl: Number = 300,
    never_die: bool = False,
    cache_key_func: CacheKeyFunction | None = None,
    ignore_fields: tuple[str, ...] = (),
) -> Callable[[F], F]:
    """In-memory cache decorator. See `base_cache` for full documentation."""
    _start_cache_clear_thread()
    return base_cache(ttl, never_die, cache_key_func, ignore_fields, _MEMORY_CONFIG)
