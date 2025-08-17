from redis.asyncio import Redis
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    _instance: Redis | None = None

    @classmethod
    async def get_instance(cls) -> Redis:
        if cls._instance is None:
            try:
                url = 'redis://red-d2f0hhc9c44c739gk3g0:6379'
                # Базовая конфигурация для локального Redis без пароля
                cls._instance = Redis.from_url(url, decode_responses=True)

                if not await cls._instance.ping():
                    raise ConnectionError("Redis ping failed")
                logger.info("Redis connection established")
            except Exception as e:
                cls._instance = None
                logger.error(f"Redis connection error: {e}")
                raise
        return cls._instance

    @classmethod
    async def close(cls) -> None:
        if cls._instance:
            await cls._instance.close()
            cls._instance = None