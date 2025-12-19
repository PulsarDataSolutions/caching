# Python Caching Library

A simple and robust caching library for Python functions, supporting both synchronous and asynchronous code.

## Features

- Cache function results based on function ID and arguments
- Supports both synchronous and asynchronous functions
- Thread-safe locking to prevent duplicate calculations
- Configurable Time-To-Live (TTL) for cached items
- "Never Die" mode for functions that should keep cache refreshed automatically
- Skip cache functionality to force fresh function execution while updating cache

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

# Cache function results for 5 minutes (default)
@cache()
def expensive_calculation(a, b):
    # Some expensive operation
    return a + b

# Async cache with custom TTL (1 hour)
@cache(ttl=3600)
async def another_calculation(url):
    # Some expensive IO call
    return requests.get(url).json()
```

### Never Die Cache

The `never_die` feature ensures that cached values never expire by automatically refreshing them in the background:

```python
# Cache with never_die (automatic refresh)
@cache(ttl=300, never_die=True)
def critical_operation(user_id):
    # Expensive operation that should always be available from cache
    return fetch_data_from_database(user_id)
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
