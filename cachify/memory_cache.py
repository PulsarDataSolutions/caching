import asyncio
import threading
from collections import defaultdict
from typing import Callable

from cachify.cache import base_cache
from cachify.storage.memory_storage import MemoryStorage
from cachify.types import CacheConfig, CacheKeyFunction, F, Number

_CACHE_CLEAR_THREAD: threading.Thread | None = None
_CACHE_CLEAR_LOCK: threading.Lock = threading.Lock()

_ASYNC_LOCKS: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
_SYNC_LOCKS: defaultdict[str, threading.Lock] = defaultdict(threading.Lock)

_MEMORY_CONFIG = CacheConfig(
    storage=MemoryStorage,
    sync_lock=_SYNC_LOCKS.__getitem__,
    async_lock=_ASYNC_LOCKS.__getitem__,
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
