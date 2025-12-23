import asyncio
import pytest

from caching.memory_cache import cache

TTL = 0.1


@pytest.mark.asyncio
async def test_neverdie_vs_regular():
    """
    Compare never_die and regular caching side by side to demonstrate
    the key difference in behavior.
    """
    neverdie_counter = 0
    regular_counter = 0

    @cache(ttl=TTL, never_die=True)
    async def neverdie_fn() -> int:
        nonlocal neverdie_counter
        neverdie_counter += 1
        return neverdie_counter

    @cache(ttl=TTL, never_die=False)
    async def regular_fn() -> int:
        nonlocal regular_counter
        regular_counter += 1
        return regular_counter

    # First call initializes the cache
    await regular_fn()
    await neverdie_fn()

    # Wait for some time to allow background refreshes to occur
    wait_time = TTL * 4
    await asyncio.sleep(wait_time)

    # The never_die counter should have been incremented by background refreshes
    assert neverdie_counter > 2, f"Never-die should auto-refresh, counter: {neverdie_counter}"

    # The regular counter should still be 1 (no auto-refresh)
    assert regular_counter == 1, f"Regular should NOT auto-refresh, counter: {regular_counter}"

    # Both functions should return their current counter values
    assert await neverdie_fn() == neverdie_counter
    assert await regular_fn() == regular_counter


@pytest.mark.asyncio
async def test_neverdie_exception():
    neverdie_counter = 0

    @cache(ttl=TTL, never_die=True)
    async def neverdie_fn() -> int:
        nonlocal neverdie_counter
        neverdie_counter += 1
        if neverdie_counter > 2:
            raise RuntimeError("Simulated failure")
        return neverdie_counter

    # First call initializes the cache
    await neverdie_fn()

    # Wait some time to allow background refreshes to occur
    await asyncio.sleep(TTL * 5)

    # At this point, the function got stuck at returning just 3
    assert await neverdie_fn() == 2
    assert neverdie_counter > 2
