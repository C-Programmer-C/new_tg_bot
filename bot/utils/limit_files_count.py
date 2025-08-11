import logging
from functools import wraps
from aiogram.types import Message
from typing import Callable, Awaitable, Any
from redis.asyncio import Redis

from bot.clients.redis_client import RedisClient
from bot.config import settings

MAX_COUNT_FILES = settings.MAX_COUNT_FILES

logger = logging.getLogger(__name__)

def file_upload_limit(limit: int = MAX_COUNT_FILES):
    def decorator(handler: Callable[..., Awaitable[Any]]):
        @wraps(handler)
        async def wrapper(message: Message, *args, **kwargs):
            redis: Redis = await RedisClient.get_instance()
            user_id = message.from_user.id
            key = f"media_processing:{user_id}"

            try:
                current_count = await redis.get(key)
                current_count = int(current_count or 0)

                if current_count >= limit:
                    await message.answer(
                        f"📦 Вы уже загрузили {current_count} файлов.\n"
                        f"Максимальное количество — {limit}. Пожалуйста, удалите часть файлов или завершите процесс, прежде чем продолжить."
                    )
                    return None
            except Exception as e:
                logger.exception(f"Ошибка при проверке лимита файлов: {e}")
                await message.answer("⚠️ Не удалось проверить лимит загружаемых файлов. Попробуйте позже.")
                return None

            return await handler(message, *args, **kwargs)
        return wrapper
    return decorator
