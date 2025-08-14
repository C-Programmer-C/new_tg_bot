import asyncio
import json
import logging
from csv import excel
from typing import Any, Dict, List, Optional

from bot.clients.redis_client import RedisClient
from config import settings

CACHE_TTL_SECONDS = settings.PYRUS_IDEMPOTENT_TTL

async def get_cache(
    task_id: int,
    redis_key_template: str = "webhook_user_id_{task_id}",
) -> Optional[Any]:


    cache_key = redis_key_template.format(task_id=task_id)

    redis = await RedisClient.get_instance()

    # 2. Попытка получить из кеша
    try:
        cached_value = await redis.get(cache_key)
        return cached_value
    except Exception as e:
        logging.error(e)
        return None

async def save_cache(
    task_id: int,
    value: int,
    ttl: int
):
    try:
        redis = await RedisClient.get_instance()
        cache_key = f"webhook_user_id_{value}"
        set_result = await redis.set(cache_key, value, ex=ttl)
        logging.info(f"user_id был успешно сохранен в Redis у задачи с id: {task_id}")
        return set_result
    except Exception as e:
        logging.error(f"Ошибка при сохранении в кэш: {e}")
        return False



async def find_user_id(
    payload: Dict[str, Any],
):
    current_id = settings.VALUE_ID
    task = payload.get("task")
    fields = task.get("fields")
    for field in fields:
        found_id = field.get("id")
        if found_id == current_id:
            value = field.get("value")
            return value
    return None
