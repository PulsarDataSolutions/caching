import contextlib
import time
from dataclasses import dataclass, field
from inspect import Signature
from typing import Any

from caching.types import CacheKeyFunction, Number

_CACHE_CLEAR_INTERVAL_SECONDS: int = 10


@dataclass
class CacheEntry:
    result: Any
    ttl: float | None

    cached_at: float = field(init=False)
    expires_at: float = field(init=False)

    @classmethod
    def time(cls) -> float:
        return time.monotonic()

    def __post_init__(self):
        self.cached_at = self.time()
        self.expires_at = 0 if self.ttl is None else self.cached_at + self.ttl

    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return self.time() > self.expires_at


class MemoryStorage:
    """In-memory cache storage implementing CacheStorage protocol."""

    _CACHE: dict[tuple[str, str], CacheEntry] = {}

    @classmethod
    def clear_expired_cached_items(cls):
        """Clear expired cached items from the cache."""
        while True:
            with contextlib.suppress(Exception):
                for key, entry in list(cls._CACHE.items()):
                    if entry.is_expired():
                        del cls._CACHE[key]

            time.sleep(_CACHE_CLEAR_INTERVAL_SECONDS)

    @classmethod
    def set(cls, function_id: str, cache_key: str, result: Any, ttl: Number | None) -> None:
        cls._CACHE[function_id, cache_key] = CacheEntry(result, ttl)

    @classmethod
    def get(cls, function_id: str, cache_key: str, skip_cache: bool) -> CacheEntry | None:
        if skip_cache:
            return None
        if entry := cls._CACHE.get((function_id, cache_key)):
            if not entry.is_expired():
                return entry
        return None

    @classmethod
    def is_expired(cls, function_id: str, cache_key: str) -> bool:
        if entry := cls._CACHE.get((function_id, cache_key)):
            return entry.is_expired()
        return True

    @classmethod
    async def aset(cls, function_id: str, cache_key: str, result: Any, ttl: Number | None) -> None:
        cls.set(function_id, cache_key, result, ttl)

    @classmethod
    async def aget(cls, function_id: str, cache_key: str, skip_cache: bool) -> CacheEntry | None:
        return cls.get(function_id, cache_key, skip_cache)

    @classmethod
    async def ais_expired(cls, function_id: str, cache_key: str) -> bool:
        return cls.is_expired(function_id, cache_key)

    @classmethod
    def clear(cls):
        cls._CACHE.clear()

    @classmethod
    def create_cache_key(
        cls,
        function_signature: Signature,
        cache_key_func: CacheKeyFunction | None,
        ignore_fields: tuple[str, ...],
        args: tuple,
        kwargs: dict,
    ) -> str:
        if not cache_key_func:
            items = tuple(cls.iter_arguments(function_signature, args, kwargs, ignore_fields))
            return str(hash(items))

        cache_key = cache_key_func(args, kwargs)
        try:
            return str(hash(cache_key))
        except TypeError as exc:
            raise ValueError(
                "Cache key function must return a hashable cache key - be careful with mutable types (list, dict, set) and non built-in types"
            ) from exc

    @classmethod
    def iter_arguments(cls, function_signature: Signature, args: tuple, kwargs: dict, ignore_fields: tuple[str, ...]):
        bound = function_signature.bind_partial(*args, **kwargs)
        bound.apply_defaults()

        for name, value in bound.arguments.items():
            if name in ignore_fields:
                continue

            param = function_signature.parameters[name]

            if param.kind == param.VAR_POSITIONAL:
                yield from value
                continue

            if param.kind == param.VAR_KEYWORD:
                yield from value.items()
                continue

            yield name, value
