"""
Redis cache tests require a running Redis instance.
Set REDIS_URL environment variable or use default localhost:6379.

To run these tests:
    pytest pytest/tests/redis/ -v

To skip Redis tests when Redis is not available:
    pytest pytest/tests/ -v --ignore=pytest/tests/redis/
"""
