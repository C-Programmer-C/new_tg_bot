import asyncio
import json
import logging
from redis.asyncio import Redis

from bot.clients.redis_client import RedisClient
from config import settings
from webhook.notify_user_and_clear_state import notify_user_and_clear_state

logging.basicConfig(level=logging.INFO)

# Настройки
QUEUE_KEY = "pyrus:event:queue"
COMMENTS_TTL = settings.PYRUS_IDEMPOTENT_TTL
LOCK_TTL = 30  # сек

redis_client: Redis | None = None

# ---------- Продюсер ----------
async def process_event(event):
    """
    Вместо обработки сразу — кладём в очередь Redis.
    """
    task_id = event.get("task_id")
    redis = await RedisClient.get_instance()
    event_json = json.dumps(event)
    await redis.rpush(QUEUE_KEY, event_json)
    logging.info(f"[QUEUE] Добавлено событие task_id={task_id}")


# ---------- Воркер ----------
async def worker():
    redis = await RedisClient.get_instance()
    await redis.flushall()
    logging.info(f"[WORKER] Слушаю очередь {QUEUE_KEY}...")

    while True:
        try:
            logging.info("[WORKER] Ожидаю событие...")
            result = await redis.blpop([QUEUE_KEY], timeout=0)  # ждать бесконечно

            if not result:
                print("Результата нет")
                continue

            _, event = result

            event = json.loads(event)

            task_id = event.get("task_id")
            lock_key = f"lock:task:{task_id}"

            # Локировка на время обработки
            if not await redis.set(lock_key, "1", ex=LOCK_TTL, nx=True):
                logging.info(f"[SKIP] Задача {task_id} уже обрабатывается")
                continue

            try:
                logging.info(f"[PROCESS] task_id={task_id}, event={event.get('event')}")

                comments_with_channel = [
                    c for c in (event.get("task", {}).get("comments") or [])
                    if c.get("channel") is not None or c.get("action") == "reopened"
                ]
                if not comments_with_channel:
                    logging.info(f"[NO COMMENTS] Нет комментариев с channel у {task_id}")
                    continue

                with open("comments.json", "w", encoding="utf-8") as f:
                    json.dump(list(reversed(comments_with_channel)), f, indent=4, ensure_ascii=False)

                user_id = event.get("user_id")
                print(user_id)
                for c in reversed(comments_with_channel):
                    comment_key = f"comment:{c['id']}"

                    logging.info(f"Обрабатывается комментарий с id: {c['id']}")

                    if c.get("action") == "reopened":
                        logging.info(f"[STOP-REOPENED] Обработан комментарий с id: {c['id']} с событием 'Переоткрытие задачи', — останавливаемся.")
                        break

                    if await redis.exists(comment_key):
                        logging.info(f"[STOP-DUP] {c['id']} уже обработан")
                        break

                    await redis.set(comment_key, "1", ex=COMMENTS_TTL)
                    logging.info(f"[NEW] {c['id']} сохранён в Redis")

                    text = c.get("text")
                    message_id = c.get("id")
                    asyncio.create_task(notify_user_and_clear_state(user_id, text, message_id))

                    logging.info(f"[PROCESS] комментарий {c['id']} успешно обработан!")

                logging.info(f"[DONE] Задача c id: {task_id} успешно обработана!")

            finally:
                await redis.delete(lock_key)

        except Exception as e:
            logging.exception(f"[ERROR] Worker поймал исключение: {e}")
            await asyncio.sleep(1)  # Пауза, чтобы не крутить цикл слишком быстро


# ---------- Точка входа для воркера ----------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,  # 👈 теперь будут видны debug-сообщения
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    asyncio.run(worker())