import pytest
import redis

from caching import reset_redis_config, setup_redis_config


def test_setup_requires_at_least_one_client():
    """Test that setup_redis_config raises if no client provided."""
    with pytest.raises(ValueError, match="At least one"):
        setup_redis_config()


def test_setup_cannot_be_called_twice(sync_redis_client: redis.Redis):
    """Test that setup_redis_config raises if called twice without reset."""
    setup_redis_config(sync_client=sync_redis_client)

    with pytest.raises(RuntimeError, match="already set"):
        setup_redis_config(sync_client=sync_redis_client)


def test_reset_allows_reconfiguration(sync_redis_client: redis.Redis):
    """Test that reset_redis_config allows calling setup again."""
    setup_redis_config(sync_client=sync_redis_client, key_prefix="test1")
    reset_redis_config()
    setup_redis_config(sync_client=sync_redis_client, key_prefix="test2")
    # Should not raise


def test_invalid_on_error_value(sync_redis_client: redis.Redis):
    """Test that invalid on_error value raises."""
    with pytest.raises(ValueError, match="on_error"):
        setup_redis_config(sync_client=sync_redis_client, on_error="invalid")  # type: ignore


def test_config_values_are_stored(sync_redis_client: redis.Redis):
    """Test that config values are correctly stored."""
    from caching import get_redis_config

    setup_redis_config(
        sync_client=sync_redis_client,
        key_prefix="myprefix",
        lock_timeout=30,
        on_error="raise",
    )

    config = get_redis_config()
    assert config.sync_client is sync_redis_client
    assert config.async_client is None
    assert config.key_prefix == "myprefix"
    assert config.lock_timeout == 30
    assert config.on_error == "raise"


def test_get_config_before_setup_raises():
    """Test that get_redis_config raises if not configured."""
    from caching import get_redis_config

    with pytest.raises(RuntimeError, match="not configured"):
        get_redis_config()


def test_unpicklable_object_raises_error(setup_sync_redis: redis.Redis):
    """Test that caching unpicklable objects raises a clear error."""
    from caching import redis_cache

    @redis_cache(ttl=60)
    def get_lambda():
        return lambda x: x * 2  # lambdas are not picklable

    with pytest.raises(TypeError, match="cannot be pickled"):
        get_lambda()
