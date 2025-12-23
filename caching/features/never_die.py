import asyncio
import functools
import inspect
import threading
import time
from asyncio import AbstractEventLoop
from concurrent.futures import Future as ConcurrentFuture
from dataclasses import dataclass
from typing import Any, Callable

from caching.config import logger
from caching.storage.memory_storage import MemoryStorage
from caching.types import CacheConfig, CacheKeyFunction, Number
from caching.utils.functions import get_function_id

_NEVER_DIE_THREAD: threading.Thread | None = None
_NEVER_DIE_LOCK: threading.Lock = threading.Lock()
_NEVER_DIE_REGISTRY: list["NeverDieCacheEntry"] = []
_NEVER_DIE_CACHE_THREADS: dict[str, threading.Thread] = {}
_NEVER_DIE_CACHE_FUTURES: dict[str, ConcurrentFuture] = {}

_MAX_BACKOFF: int = 10
_BACKOFF_MULTIPLIER: float = 1.25
_REFRESH_INTERVAL_SECONDS: float = 0.1


@dataclass
class NeverDieCacheEntry:
    function: Callable[..., Any]
    ttl: Number
    args: tuple
    kwargs: dict
    cache_key_func: CacheKeyFunction | None
    ignore_fields: tuple[str, ...]
    loop: AbstractEventLoop | None
    config: CacheConfig

    def __post_init__(self):
        self._backoff: float = 1
        self._expires_at: float = time.monotonic() + self.ttl

    @functools.cached_property
    def id(self) -> str:
        return get_function_id(self.function)

    @functools.cached_property
    def cache_key(self) -> str:
        function_signature = inspect.signature(self.function)
        return MemoryStorage.create_cache_key(
            function_signature,
            self.cache_key_func,
            self.ignore_fields,
            self.args,
            self.kwargs,
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, NeverDieCacheEntry):
            return False
        return self.id == other.id and self.cache_key == other.cache_key

    def __hash__(self) -> int:
        return hash((self.id, self.cache_key))

    def is_expired(self) -> bool:
        return time.monotonic() > self._expires_at

    def reset(self):
        self._backoff = 1
        self._expires_at = time.monotonic() + self.ttl

    def revive(self):
        self._backoff = min(self._backoff * _BACKOFF_MULTIPLIER, _MAX_BACKOFF)
        self._expires_at = time.monotonic() + self.ttl * self._backoff


def _run_sync_function_and_cache(entry: NeverDieCacheEntry):
    """Run a function and cache its result"""
    with entry.config.sync_lock(entry.id, entry.cache_key):
        try:
            result = entry.function(*entry.args, **entry.kwargs)
            entry.config.storage.set(entry.id, entry.cache_key, result, None)
            entry.reset()
        except BaseException:
            entry.revive()
            logger.debug(
                f"Exception caching {entry.function.__qualname__}, reviving previous entry",
                exc_info=True,
            )


async def _run_async_function_and_cache(entry: NeverDieCacheEntry):
    """Run a function and cache its result"""
    async with entry.config.async_lock(entry.id, entry.cache_key):
        try:
            result = await entry.function(*entry.args, **entry.kwargs)
            await entry.config.storage.aset(entry.id, entry.cache_key, result, None)
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
        if thread.is_alive():
            continue
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

                try:
                    coroutine = _run_async_function_and_cache(entry)
                    future = asyncio.run_coroutine_threadsafe(coroutine, entry.loop)
                except RuntimeError:
                    coroutine.close()
                    logger.debug(f"Loop is closed for {entry.function.__qualname__}, skipping future creation")
                    continue

                _NEVER_DIE_CACHE_FUTURES[entry.cache_key] = future
        finally:
            time.sleep(_REFRESH_INTERVAL_SECONDS)
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
    config: CacheConfig,
):
    """Register a function for never_die cache refreshing"""
    is_async = inspect.iscoroutinefunction(function)

    entry = NeverDieCacheEntry(
        function=function,
        ttl=ttl,
        args=args,
        kwargs=kwargs,
        cache_key_func=cache_key_func,
        ignore_fields=ignore_fields,
        loop=asyncio.get_running_loop() if is_async else None,
        config=config,
    )

    with _NEVER_DIE_LOCK:
        if entry not in _NEVER_DIE_REGISTRY:
            _NEVER_DIE_REGISTRY.append(entry)

    _start_never_die_thread()


def clear_never_die_registry():
    """
    Clear all entries from the never_die registry.

    Useful for testing to prevent background threads from
    accessing resources that have been cleaned up.
    """
    with _NEVER_DIE_LOCK:
        _NEVER_DIE_REGISTRY.clear()
        _NEVER_DIE_CACHE_THREADS.clear()
        _NEVER_DIE_CACHE_FUTURES.clear()
