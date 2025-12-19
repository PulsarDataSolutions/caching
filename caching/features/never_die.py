import asyncio
import functools
import inspect
import threading
import time
from asyncio import AbstractEventLoop
from concurrent.futures import Future as ConcurrentFuture
from dataclasses import dataclass, field
from typing import Any, Callable

from caching._async.lock import _ASYNC_LOCKS
from caching._sync.lock import _SYNC_LOCKS
from caching.bucket import CacheBucket, MemoryBackend
from caching.config import logger
from caching.types import CacheBackend, CacheKeyFunction, Number
from caching.utils.functions import get_function_id

_NEVER_DIE_THREAD: threading.Thread | None = None
_NEVER_DIE_LOCK: threading.Lock = threading.Lock()
_NEVER_DIE_REGISTRY: list["NeverDieCacheEntry"] = []
_NEVER_DIE_CACHE_THREADS: dict[str, threading.Thread] = {}
_NEVER_DIE_CACHE_FUTURES: dict[str, ConcurrentFuture] = {}


@dataclass
class NeverDieCacheEntry:
    function: Callable[..., Any]
    ttl: Number
    args: tuple
    kwargs: dict
    cache_key_func: CacheKeyFunction | None
    ignore_fields: tuple[str, ...]
    loop: AbstractEventLoop | None
    backend: type[CacheBackend] = field(default=MemoryBackend)

    def __post_init__(self):
        self._backoff: float = 1
        self._expires_at: float = time.monotonic() + self.ttl

    @functools.cached_property
    def id(self) -> str:
        return get_function_id(self.function)

    @functools.cached_property
    def cache_key(self) -> str:
        function_signature = inspect.signature(self.function)
        return CacheBucket.create_cache_key(
            function_signature,
            self.cache_key_func,
            self.ignore_fields,
            self.args,
            self.kwargs,
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, NeverDieCacheEntry):
            return False
        return self.id == other.id and self.cache_key == other.cache_key and self.backend == other.backend

    def __hash__(self) -> int:
        return hash((self.id, self.cache_key, self.backend))

    def is_expired(self) -> bool:
        return time.monotonic() > self._expires_at

    def reset(self):
        self._backoff = 1
        self._expires_at = time.monotonic() + self.ttl

    def revive(self):
        self._backoff = min(self._backoff * 1.25, 10)
        self._expires_at = time.monotonic() + self.ttl * self._backoff


def _get_sync_lock(entry: NeverDieCacheEntry):
    """Get the appropriate sync lock for the entry's backend."""
    from caching.backends.redis import RedisBackend

    if entry.backend is not RedisBackend:
        return _SYNC_LOCKS[entry.id][entry.cache_key]

    from caching.backends.redis_lock import RedisLockManager

    return RedisLockManager.sync_lock(entry.id, entry.cache_key)


def _get_async_lock(entry: NeverDieCacheEntry):
    """Get the appropriate async lock for the entry's backend."""
    from caching.backends.redis import RedisBackend

    if entry.backend is not RedisBackend:
        return _ASYNC_LOCKS[entry.id][entry.cache_key]

    from caching.backends.redis_lock import RedisLockManager

    return RedisLockManager.async_lock(entry.id, entry.cache_key)


def _run_sync_function_and_cache(entry: NeverDieCacheEntry):
    """Run a function and cache its result"""
    try:
        lock = _get_sync_lock(entry)
    except RuntimeError:
        # Backend no longer available (e.g., Redis was reset)
        return

    with lock:
        try:
            result = entry.function(*entry.args, **entry.kwargs)
            entry.backend.set(entry.id, entry.cache_key, result, None)
            entry.reset()
        except BaseException:
            entry.revive()
            logger.debug(
                f"Exception caching {entry.function.__qualname__}, reviving previous entry",
                exc_info=True,
            )


async def _run_async_function_and_cache(entry: NeverDieCacheEntry):
    """Run a function and cache its result"""
    try:
        lock = _get_async_lock(entry)
    except RuntimeError:
        # Backend no longer available (e.g., Redis was reset)
        return

    async with lock:
        try:
            result = await entry.function(*entry.args, **entry.kwargs)
            await entry.backend.aset(entry.id, entry.cache_key, result, None)
            entry.reset()
        except BaseException:
            entry.revive()
            logger.debug(
                f"Exception caching {entry.function.__qualname__}, reviving previous entry",
                exc_info=True,
            )


def _cache_is_being_set(entry: NeverDieCacheEntry) -> bool:
    if entry.loop:
        return entry.cache_key in _NEVER_DIE_CACHE_FUTURES and not _NEVER_DIE_CACHE_FUTURES[entry.cache_key].done()
    return entry.cache_key in _NEVER_DIE_CACHE_THREADS and _NEVER_DIE_CACHE_THREADS[entry.cache_key].is_alive()


def _clear_dead_futures():
    """Clear dead futures from the cache future registry"""
    for cache_key, thread in list(_NEVER_DIE_CACHE_FUTURES.items()):
        if thread.done():
            del _NEVER_DIE_CACHE_FUTURES[cache_key]


def _clear_dead_threads():
    """Clear dead threads from the cache thread registry"""
    for cache_key, thread in list(_NEVER_DIE_CACHE_THREADS.items()):
        if not thread.is_alive():
            del _NEVER_DIE_CACHE_THREADS[cache_key]


def _refresh_never_die_caches():
    """Background thread function that periodically refreshes never_die cache entries"""
    while True:
        try:
            for entry in list(_NEVER_DIE_REGISTRY):
                if not entry.is_expired():
                    continue

                if _cache_is_being_set(entry):
                    continue

                if not entry.loop:  # sync
                    thread = threading.Thread(target=_run_sync_function_and_cache, args=(entry,), daemon=True)
                    thread.start()
                    _NEVER_DIE_CACHE_THREADS[entry.cache_key] = thread
                    continue

                if entry.loop.is_closed():
                    logger.debug(f"Loop is closed for {entry.function.__qualname__}, skipping future creation")
                    continue

                # Doesn't actually run, just creates a coroutine
                coroutine = _run_async_function_and_cache(entry)

                try:
                    future = asyncio.run_coroutine_threadsafe(coroutine, entry.loop)
                except RuntimeError:
                    coroutine.close()
                    logger.debug(f"Loop is closed for {entry.function.__qualname__}, skipping future creation")
                    continue

                _NEVER_DIE_CACHE_FUTURES[entry.cache_key] = future

        finally:
            time.sleep(0.1)
            _clear_dead_futures()
            _clear_dead_threads()


def _start_never_die_thread():
    """Start the background thread if it's not already running"""
    global _NEVER_DIE_THREAD
    with _NEVER_DIE_LOCK:
        if _NEVER_DIE_THREAD and _NEVER_DIE_THREAD.is_alive():
            return
        _NEVER_DIE_THREAD = threading.Thread(target=_refresh_never_die_caches, daemon=True)
        _NEVER_DIE_THREAD.start()


def register_never_die_function(
    function: Callable[..., Any],
    ttl: Number,
    args: tuple,
    kwargs: dict,
    cache_key_func: CacheKeyFunction | None,
    ignore_fields: tuple[str, ...],
    backend: type[CacheBackend] = MemoryBackend,
) -> None:
    """Register a function for never_die cache refreshing (memory backend)"""
    is_async = inspect.iscoroutinefunction(function)

    try:
        loop = asyncio.get_running_loop() if is_async else None
    except RuntimeError:
        loop = None

    entry = NeverDieCacheEntry(
        function,
        ttl,
        args,
        kwargs,
        cache_key_func,
        ignore_fields,
        loop,
        backend,
    )

    with _NEVER_DIE_LOCK:
        if entry not in _NEVER_DIE_REGISTRY:
            _NEVER_DIE_REGISTRY.append(entry)

    _start_never_die_thread()


def register_never_die_function_redis(
    function: Callable[..., Any],
    ttl: Number,
    args: tuple,
    kwargs: dict,
    cache_key_func: CacheKeyFunction | None,
    ignore_fields: tuple[str, ...],
    backend: type[CacheBackend],
) -> None:
    """Register a function for never_die cache refreshing (Redis backend)"""
    from caching.backends.redis import RedisBackend

    register_never_die_function(
        function,
        ttl,
        args,
        kwargs,
        cache_key_func,
        ignore_fields,
        RedisBackend,
    )
