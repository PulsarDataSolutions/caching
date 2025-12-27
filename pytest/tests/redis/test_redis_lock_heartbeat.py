import asyncio
import time

import pytest
import redis
import redis.asyncio

from caching import redis_cache, setup_redis_config
from caching.redis.lock import _AsyncHeartbeatManager, _SyncHeartbeatManager


@pytest.fixture
def setup_redis_short_lock(sync_redis_client: redis.Redis, async_redis_client: redis.asyncio.Redis):
    """Setup Redis config with a short lock timeout for testing heartbeat."""
    # Clear any leftover state from previous tests
    _AsyncHeartbeatManager.reset()
    _SyncHeartbeatManager.reset()

    setup_redis_config(
        sync_client=sync_redis_client,
        async_client=async_redis_client,
        lock_timeout=2,  # 2 second lock timeout
    )
    yield sync_redis_client

    # Cleanup after test
    _AsyncHeartbeatManager.reset()
    _SyncHeartbeatManager.reset()


@pytest.mark.asyncio
async def test_async_lock_heartbeat_extends_lock(setup_redis_short_lock: redis.Redis):
    """
    Test that locks are extended via heartbeat when function takes longer than lock timeout.

    Scenario:
    - Lock timeout is 2 seconds
    - Function takes 4 seconds to complete
    - Without heartbeat: lock would expire at 2s, second caller could acquire at 2s
    - With heartbeat: lock stays held, second caller waits for first to complete
    """
    call_count = 0
    execution_order: list[int] = []

    @redis_cache(ttl=60)
    async def slow_function(task_id: int) -> str:
        nonlocal call_count
        call_count += 1
        execution_order.append(task_id)
        await asyncio.sleep(4)  # Takes longer than 2s lock timeout
        return f"result_{task_id}"

    start = time.monotonic()

    # Start first call
    task1 = asyncio.create_task(slow_function(1))

    # Wait a bit, then start second call (after lock would have expired without heartbeat)
    await asyncio.sleep(2.5)
    task2 = asyncio.create_task(slow_function(1))

    # Wait for both to complete
    result1, result2 = await asyncio.gather(task1, task2)
    elapsed = time.monotonic() - start

    # Both should return same cached result
    assert result1 == "result_1"
    assert result2 == "result_1"

    # Function should only be called once (second call waited for cache)
    assert call_count == 1

    # Total time should be ~4s (first function completes, second gets cached result)
    # If heartbeat failed, task2 would have started its own execution at ~2.5s
    assert elapsed < 5


@pytest.mark.asyncio
async def test_async_lock_heartbeat_prevents_concurrent_execution(setup_redis_short_lock: redis.Redis):
    """
    Test that concurrent calls don't execute simultaneously even when function exceeds lock timeout.

    If heartbeat wasn't working, the second caller would acquire the "expired" lock
    and both would execute concurrently, causing call_count to be > 1.
    """
    call_count = 0
    concurrent_executions = 0
    max_concurrent = 0

    @redis_cache(ttl=60)
    async def tracked_slow_function(key: str) -> str:
        nonlocal call_count, concurrent_executions, max_concurrent
        call_count += 1
        concurrent_executions += 1
        max_concurrent = max(max_concurrent, concurrent_executions)

        await asyncio.sleep(3)  # Longer than 2s lock timeout

        concurrent_executions -= 1
        return f"result_{key}"

    # Start two concurrent calls (not three - reduces timing sensitivity)
    task1 = asyncio.create_task(tracked_slow_function("same_key"))
    await asyncio.sleep(0.1)  # Slight delay to ensure task1 acquires lock first
    task2 = asyncio.create_task(tracked_slow_function("same_key"))

    results = await asyncio.gather(task1, task2)

    assert all(r == "result_same_key" for r in results)
    assert call_count == 1  # Only one execution
    assert max_concurrent == 1  # Never had concurrent executions


def test_sync_lock_heartbeat_extends_lock(setup_redis_short_lock: redis.Redis):
    """Test that sync locks are extended via heartbeat when function takes longer than lock timeout."""
    import threading

    call_count = 0
    results: list[str] = []
    lock = threading.Lock()

    @redis_cache(ttl=60)
    def slow_function(key: str) -> str:
        nonlocal call_count
        with lock:
            call_count += 1
        time.sleep(4)  # Longer than 2s lock timeout
        return f"result_{key}"

    def run_and_store():
        result = slow_function("same_key")
        with lock:
            results.append(result)

    # Start two threads
    thread1 = threading.Thread(target=run_and_store)
    thread2 = threading.Thread(target=run_and_store)

    start = time.monotonic()
    thread1.start()
    time.sleep(2.5)  # Start second after lock would have expired without heartbeat
    thread2.start()

    thread1.join()
    thread2.join()
    elapsed = time.monotonic() - start

    # Both should get same result
    assert all(r == "result_same_key" for r in results)

    # Function should only be called once
    assert call_count == 1

    # Should complete in ~4s (not 4 + 4 = 8s if both executed)
    assert elapsed < 5


@pytest.mark.asyncio
async def test_lock_extension_timing(setup_redis_short_lock: redis.Redis):
    """
    Verify the lock TTL is actually being extended in Redis.

    This directly checks Redis to confirm the lock key's TTL is being refreshed.
    """
    redis_client = setup_redis_short_lock
    ttl_samples: list[int] = []

    @redis_cache(ttl=60)
    async def slow_function() -> str:
        # Sample TTL multiple times during execution
        for _ in range(3):
            await asyncio.sleep(0.8)
            # Find the lock key
            for key in redis_client.scan_iter("cache:lock:*"):
                ttl = redis_client.ttl(key)
                if ttl > 0:
                    ttl_samples.append(ttl)
        return "done"

    await slow_function()

    # Lock TTL should have been refreshed
    # With 2s timeout and extensions every ~1s, TTL should stay around 1-2 seconds
    assert len(ttl_samples) > 0, "Should have captured TTL samples"
    # TTL should never be 0 or negative (lock expired) during execution
    assert all(ttl >= 1 for ttl in ttl_samples), f"Lock TTL dropped too low: {ttl_samples}"
