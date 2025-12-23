# Python Caching Library

A simple and robust caching library for Python functions, supporting both synchronous and asynchronous code.

## Features

- Cache function results based on function ID and arguments
- Supports both synchronous and asynchronous functions
- Thread-safe locking to prevent duplicate calculations
- Configurable Time-To-Live (TTL) for cached items
- "Never Die" mode for functions that should keep cache refreshed automatically
- Skip cache functionality to force fresh function execution while updating cache
- Redis caching for distributed caching across multiple processes/machines

## Installation

```bash
# Clone the repository
git clone https://github.com/PulsarDefi/caching.git
cd caching

# Install the package
poetry install
```

## Usage

### Basic Usage

```python
from caching import cache

# Cache function in sync functions
@cache(ttl=60) # ttl in seconds
def expensive_calculation(a, b):
    # Some expensive operation
    return a + b

# And async functions
@cache(ttl=3600) # ttl in seconds
async def another_calculation(url):
    # Some expensive IO call
    return await httpx.get(url).json()
```

### Redis Cache

For distributed caching across multiple processes or machines, use `rcache`:

```python
import redis
from caching import setup_redis_config, rcache

# Configure Redis (call once at startup)
setup_redis_config(
    sync_client=redis.from_url("redis://localhost:6379/0"),
    key_prefix="myapp",       # default: "cache", prefix searchable on redis "PREFIX:*"
    lock_timeout=10,          # default: 10
    on_error="silent",        # "silent" (default) or "raise" in case of redis errors
)

@rcache(ttl=300)
def get_user(user_id: int) -> dict:
    return fetch_from_database(user_id)

# Async version
import redis.asyncio as aredis

setup_redis_config(async_client=aredis.from_url("redis://localhost:6379/0"))

@rcache(ttl=300)
def get_user_async(user_id: int) -> dict:
    return await fetch_from_database(user_id)
```

### Never Die Cache

The `never_die` feature ensures that cached values never expire by automatically refreshing them in the background:

```python
# Cache with never_die (automatic refresh)
@cache(ttl=300, never_die=True)
def critical_operation(data_id: str):
    # Expensive operation that should always be available from cache
    return fetch_data_from_database(data_id)
```

**How Never Die Works:**

1. When a function with `never_die=True` is first called, the result is cached
2. A background thread monitors all `never_die` functions
3. Before the cache expires (at 90% of TTL), the function is automatically called again
4. The cache is updated with the new result
5. If the refresh operation fails, the existing cached value is preserved
6. Clients always get fast response times by reading from cache

**Benefits:**

- Cache is always "warm" and ready to serve
- No user request ever has to wait for the expensive operation
- If backend services go down temporarily, the last successful result is still available
- Perfect for critical operations where latency must be minimized

### Skip Cache

The `skip_cache` feature allows you to bypass reading from cache while still updating it with fresh results:

```python
@cache(ttl=300)
def get_user_data(user_id):
    # Expensive operation to fetch user data
    return fetch_from_database(user_id)

# Normal call - uses cache if available
user = get_user_data(123)
# Force fresh execution while updating cache
fresh_user = get_user_data(123, skip_cache=True)
# Next normal call will get the updated cached value
updated_user = get_user_data(123)
```

**How Skip Cache Works:**

1. When `skip_cache=True` is passed, the function bypasses reading from cache
2. The function executes normally and returns fresh results
3. The fresh result is stored in the cache, updating any existing cached value
4. Subsequent calls without `skip_cache=True` will use the updated cached value
5. The TTL timer resets from when the cache last was updated

**Benefits:**

- Force refresh of potentially stale data while keeping cache warm
- Ensuring fresh data for critical operations while maintaining cache for other calls

## Testing

Run the test scripts

```bash
poetry run python -m pytest
```

## License

MIT
