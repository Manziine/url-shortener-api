import redis.asyncio as aioredis
from app.core.config import settings

_pool = None


async def get_redis_pool():
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL, max_connections=20, decode_responses=True
        )
    return aioredis.Redis(connection_pool=_pool)


async def get_cache(key: str):
    r = await get_redis_pool()
    return await r.get(key)


async def set_cache(key: str, value: str, expire: int = 86400):
    r = await get_redis_pool()
    await r.setex(key, expire, value)


async def delete_cache(key: str):
    r = await get_redis_pool()
    await r.delete(key)


async def rate_limit_check(identifier: str, limit: int = 10, window: int = 60) -> bool:
    """Sliding window rate limit. Returns True if allowed."""
    r = await get_redis_pool()
    key = f"ratelimit:{identifier}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, window)
    return count <= limit
