from redis.asyncio import Redis
from aiogram.types import Message

async def can_reset_files(redis: Redis, user_id: int, message: Message) -> bool:
    processing_key = f"media_processing:{user_id}"
    if await redis.exists(processing_key):
        current_count = await redis.get(processing_key)
        if current_count is not None and int(current_count) > 0:
            await message.answer("⏳ Нельзя сбросить файлы во время их загрузки!")
            return False
    return True