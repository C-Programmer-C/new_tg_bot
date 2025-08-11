import time
from redis.asyncio import Redis
from bot.config import settings


async def check_cooldown(redis: Redis, cooldown_key: str) -> bool:
    """Проверяет наличие кулдауна для пользователя и устанавливает его."""
    now = int(time.time())

    cooldown = await redis.get(cooldown_key)

    if cooldown is not None:
        cooldown = int(cooldown)
        if now - cooldown < settings.COOLDOWN_SECONDS:
            return False

    # Устанавливаем значение с истечением времени
    await redis.setex(cooldown_key, settings.COOLDOWN_SECONDS, now)
    return True
