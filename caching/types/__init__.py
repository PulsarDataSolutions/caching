from dataclasses import dataclass
from typing import Any, AsyncContextManager, Callable, ContextManager, Hashable, Protocol, TypeAlias, TypedDict, TypeVar

Number: TypeAlias = int | float
CacheKeyFunction: TypeAlias = Callable[[tuple, dict], Hashable]

F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True, slots=True)
class CacheConfig:
    """Configuration for cache, grouping storage, lock, and never_die registration."""

    storage: "CacheStorage"
    sync_lock: Callable[[str, str], ContextManager]
    async_lock: Callable[[str, str], AsyncContextManager]
    register_never_die: Callable[..., None]


class CacheEntryProtocol(Protocol):
    """Protocol for cache entry objects."""

    result: Any

    def is_expired(self) -> bool: ...


class CacheStorage(Protocol):
    """Protocol defining the interface for cache storage."""

    def get(self, function_id: str, cache_key: str, skip_cache: bool) -> CacheEntryProtocol | None:
        """Retrieve a cache entry. Returns None if not found, expired, or skip_cache is True."""
        ...

    def set(self, function_id: str, cache_key: str, result: Any, ttl: Number | None) -> None:
        """Store a result in the cache with optional TTL."""
        ...

    def is_expired(self, function_id: str, cache_key: str) -> bool:
        """Check if a cache entry is expired or doesn't exist."""
        ...

    async def aget(self, function_id: str, cache_key: str, skip_cache: bool) -> CacheEntryProtocol | None:
        """Async version of get."""
        ...

    async def aset(self, function_id: str, cache_key: str, result: Any, ttl: Number | None) -> None:
        """Async version of set."""
        ...

    async def ais_expired(self, function_id: str, cache_key: str) -> bool:
        """Async version of is_expired."""
        ...


class CacheKwargs(TypedDict, total=False):
    """
    ### Description
    This type can be used in conjuction with `Unpack` to provide static type
    checking for the parameters added by the `@cache()` decorator.

    This type is completely optional and `skip_cache` will work regardless
    of what static type checkers complain about.

    ### Example
    ```
    @cache()
    def function_with_cache(**_: Unpack[CacheKwargs]): ...

    # pylance/pyright should not complain
    function_with_cache(skip_cache=True)
    ```

    ### Notes
    Prior to Python 3.11, `Unpack` is only available with typing_extensions
    """

    skip_cache: bool
