import asyncio
import threading
from collections import defaultdict
from typing import DefaultDict, TypeVar

LockType = TypeVar("LockType", asyncio.Lock, threading.Lock)


def create_lock_registry(lock_factory: type[LockType]) -> DefaultDict[str, DefaultDict[str, LockType]]:
    """Create a nested defaultdict that automatically creates locks on access."""
    return defaultdict(lambda: defaultdict(lock_factory))


ASYNC_LOCKS: DefaultDict[str, DefaultDict[str, asyncio.Lock]] = create_lock_registry(asyncio.Lock)
SYNC_LOCKS: DefaultDict[str, DefaultDict[str, threading.Lock]] = create_lock_registry(threading.Lock)
