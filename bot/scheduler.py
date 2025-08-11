import asyncio
from datetime import datetime, timezone, timedelta

from bot.clients.bot_client import BotClient
from bot.clients.redis_client import RedisClient
from bot.keyboards.create_task import CreateTaskKeyboards
from bot.services.pyrus_api_service import PyrusService
import json
import logging
from typing import List, Dict

from bot.texts.create_task import CreateTaskMessages

# Логгер
logger = logging.getLogger(__name__)


def extract_user_id(fields: List[Dict]) -> int | None:
    for field in fields:
        if field.get("id") == 72:
            return field.get("value")
    return None

async def start_task_timer(task_id: int, closed_at: str, fields: List[Dict]):
    """Запускает таймер для задачи в Redis."""

    if not closed_at:
        return None

    redis = await RedisClient.get_instance()

    closed_time = datetime.fromisoformat(closed_at.replace("Z", "+00:00"))
    expire_time = closed_time + timedelta(hours=1)

    # Проверяем, не истёк ли уже срок
    if datetime.now(timezone.utc) > expire_time:
        return False

    user_id = extract_user_id(fields)

    if user_id is None:
        return False

    # Проверяем, есть ли уже задача в Redis
    existing_ttl = await redis.ttl(f"available_task:{user_id}:{task_id}")

    # Если задача уже есть и её TTL больше оставшегося времени - не обновляем
    if existing_ttl > 0 and existing_ttl > (expire_time - datetime.now(timezone.utc)).total_seconds():
        return True



    # Сохраняем/обновляем задачу с новым TTL
    ttl_seconds = (expire_time - datetime.now(timezone.utc)).total_seconds()
    value = json.dumps({
        "task_id": task_id,
        "fields": fields,
    })
    await redis.setex(f"available_task:{user_id}:{task_id}", int(ttl_seconds), value)
    logger.info(f"Таймер для задачи с id {task_id} был успешно запущен! Общее количество секунд: {ttl_seconds}")
    return True

async def log_all_task_ttls(redis):
    cursor = "0"
    pattern = "available_task:*"
    while cursor != 0:
        cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=1000)
        for key in keys:
            ttl = await redis.ttl(key)
            logger.info(f"[{datetime.now().isoformat()}] KEY={key} TTL={ttl}s")
        cursor = int(cursor)


async def post_comment_to_user(task, fields):
    # Сразу формируем словарь для быстрого доступа по id
    field_map = {f["id"]: f.get("value") for f in fields}

    # Шаг 1: проверка поля 71
    choice = field_map.get(71)
    if isinstance(choice, dict) and choice.get("choice_id") == 2:
        return

    # Шаг 2: проверка, что комментарий еще не отправлен (поле 111)
    if field_map.get(111) == "checked":
        return

    # Шаг 3: получение user_id (поле 72)
    user_id = field_map.get(72)
    if user_id is None or (isinstance(user_id, str) and not user_id.strip()):
        return

    payload = {
        "field_updates": [
                {"id": 111, "value": "checked"}
        ]
    }

    task_id = task.get("id")

    await PyrusService.post_comment_value_fields(task_id, payload)

    # Шаг 4: формируем сообщение и отправляем
    bot = BotClient.get_instance()

    type_problem = field_map.get(1)
    message = CreateTaskMessages.get_completion_task_message(task_id, type_problem)
    await bot.send_message(chat_id=user_id, text=message, reply_markup=CreateTaskKeyboards.service_quality_keyboard(task_id))



async def periodic_task_fetcher():
    redis = await RedisClient.get_instance()
    while True:
        try:
            closed_after = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
            tasks = await PyrusService.get_closed_tasks(closed_after)
            for task in tasks:
                fields = task.get("fields", {})
                close_date = task.get("close_date")
                if not close_date:
                    continue
                await start_task_timer(task["id"], close_date, fields)
                await post_comment_to_user(task, fields)
            await log_all_task_ttls(redis)
        except Exception as e:
            logger.exception(f"Ошибка при периодическом получении задач: {e}")
        await asyncio.sleep(10)