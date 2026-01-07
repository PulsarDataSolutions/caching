from importlib.metadata import version

from .features.never_die import clear_never_die_registry
from .memory_cache import cache
from .redis import DEFAULT_KEY_PREFIX, get_redis_config, reset_redis_config, setup_redis_config
from .redis_cache import redis_cache
from .types import CacheKwargs

__version__ = version("cachify")

rcache = redis_cache

__all__ = [
    "__version__",
    "rcache",
    "clear_never_die_registry",
    "cache",
    "DEFAULT_KEY_PREFIX",
    "get_redis_config",
    "reset_redis_config",
    "setup_redis_config",
    "redis_cache",
    "CacheKwargs",
]
