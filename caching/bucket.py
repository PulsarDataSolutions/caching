"""
Backwards compatibility module.

All cache storage functionality has been moved to caching.storage.memory_storage.
This module re-exports the classes for backwards compatibility.
"""

from caching.storage.memory_storage import CacheEntry, MemoryStorage

__all__ = [
    "CacheEntry",
    "MemoryStorage",
]
