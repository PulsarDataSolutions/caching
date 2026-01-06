import time
from dataclasses import dataclass, field
from typing import Any, AsyncContextManager, Callable, ContextManager, Hashable, Protocol, TypeAlias, TypedDict, TypeVar

Number: TypeAlias = int | float
CacheKeyFunction: TypeAlias = Callable[[tuple, dict], Hashable]

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class CacheEntry:
    """Base cache entry with TTL and expiration tracking."""

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


@dataclass(frozen=True, slots=True)
class CacheConfig:
    """Configuration for cache, grouping storage, lock, never_die registration and process-isolated indicator."""

    storage: "CacheStorage"
    sync_lock: Callable[[str], ContextManager]
    async_lock: Callable[[str], AsyncContextManager]
    process_isolated: bool


class CacheEntryProtocol(Protocol):
    """Protocol for cache entry objects."""

    result: Any

    def is_expired(self) -> bool: ...


class CacheStorage(Protocol):
    """Protocol defining the interface for cache storage."""

    def get(self, cache_key: str, skip_cache: bool) -> CacheEntryProtocol | None:
        """Retrieve a cache entry. Returns None if not found, expired, or skip_cache is True."""
        ...

    def set(self, cache_key: str, result: Any, ttl: Number | None):
        """Store a result in the cache with optional TTL."""
        ...

    async def aget(self, cache_key: str, skip_cache: bool) -> CacheEntryProtocol | None:
        """Async version of get."""
        ...

    async def aset(self, cache_key: str, result: Any, ttl: Number | None):
        """Async version of set."""
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
