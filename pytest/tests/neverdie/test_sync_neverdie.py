import time

from caching.cache import cache

TTL = 0.1


def test_neverdie_vs_regular():
    """
    Compare never_die and regular caching side by side to demonstrate
    the key difference in behavior.
    """
    regular_counter = 0
    neverdie_counter = 0

    @cache(ttl=TTL, never_die=False)
    def regular_fn() -> int:
        nonlocal regular_counter
        regular_counter += 1
        return regular_counter

    @cache(ttl=TTL, never_die=True)
    def neverdie_fn() -> int:
        nonlocal neverdie_counter
        neverdie_counter += 1
        return neverdie_counter

    # First call initializes the cache
    regular_fn()
    neverdie_fn()

    # Wait for some time to allow background refreshes to occur
    wait_time = TTL * 4
    time.sleep(wait_time)

    # The never_die counter should have been incremented by background refreshes
    assert neverdie_counter > 1, f"Never-die should auto-refresh, counter: {neverdie_counter}"

    # The regular counter should still be 1 (no auto-refresh)
    assert regular_counter == 1, f"Regular should NOT auto-refresh, counter: {regular_counter}"

    # Both functions should return their current counter values
    assert neverdie_fn() == neverdie_counter
    assert regular_fn() == regular_counter


def test_neverdie_exception():
    neverdie_counter = 0

    @cache(ttl=TTL, never_die=True)
    def neverdie_fn() -> int:
        nonlocal neverdie_counter
        neverdie_counter += 1
        if neverdie_counter > 2:
            raise RuntimeError("Simulated failure")
        return neverdie_counter

    # First call initializes the cache
    neverdie_fn()

    # Wait some time to allow background refreshes to occur
    time.sleep(TTL * 5)

    # At this point, the function got stuck at returning just 3
    assert neverdie_fn() == 2
    assert neverdie_counter > 2
