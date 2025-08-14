import hashlib
import json
import os
import logging
from typing import Optional, List, Dict, Any, Coroutine
from fastapi import FastAPI, Request, Header, HTTPException, BackgroundTasks, status
from bot.clients.redis_client import RedisClient
from config import settings
from webhook.get_user_id import get_cache, find_user_id, save_cache
from webhook.process_event import process_event
from redis.exceptions import RedisError
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Pyrus Webhook (FastAPI + Redis idempotency)")
IDEPT_TTL = settings.PYRUS_IDEMPOTENT_TTL


if not settings.WEBHOOK_SECURITY_KEY:
    logging.warning("PYRUS_BOT_SECRET is not set — signature verification will fail.")


# --- Простая in-memory TTL-кеш для idempotency (per-process). Для продакшна — используйте Redis. ---
_IDEMPOTENT_TTL = 60 * 60  # seconds to remember processed events
_processed_events: Dict[str, float] = {}  # event_key -> timestamp when processed


# --- Helper: create safe redis key (hashing) ---
def make_event_key(event_key: str) -> str:
    """Возвращает короткий ключ для Redis (sha256 hex)."""
    h = hashlib.sha256(event_key.encode("utf-8")).hexdigest()
    return f"pyrus:event:{h}"

# --- Idempotency using Redis SET NX EX ---
async def remember_event_redis(event_key: str, ttl: int = IDEPT_TTL) -> bool:
    """
    Возвращает True если событие новое (и сохранено в Redis), False если уже существовал.
    Если Redis не доступен — выбрасывает RedisError.
    """
    r = await RedisClient.get_instance()
    if not r:
        raise RedisError("Redis client not initialized")

    redis_key = make_event_key(event_key)
    # set NX EX - atomic
    # redis.set returns True if key was set, None if not set (already exists)
    try:
        was_set = await r.set(redis_key, b"1", nx=True, ex=ttl)
        return bool(was_set)
    except Exception as exc:
        # пробросим как RedisError для внешней обработки
        raise RedisError(str(exc))

# wrapper that tries Redis then fallback
async def remember_event(event_key: str, ttl: int = IDEPT_TTL) -> Optional[bool]:
    """
    Возвращает:
      - True -> событие новое (ключ успешно установлен в Redis)
      - False -> событие уже было (ключ уже есть)
      - None -> Redis недоступен / ошибка — вызывающий должен решить, что делать
    """
    try:
        redis_client = await RedisClient.get_instance()
    except Exception as exc:
        logging.exception("Failed to get Redis client instance")
        return None

    if redis_client is None:
        logging.warning("Redis singleton returned None")
        return None

    try:
        return await remember_event_redis(event_key, ttl)  # должен вернуть bool
    except RedisError as exc:
        logging.exception("Redis error during idempotency check")
        return None



# --- Эндпоинт вебхука ---
@app.post("/webhook")
async def pyrus_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_pyrus_sig: Optional[str] = Header(None, alias="X-Pyrus-Sig"),
    x_pyrus_retry: Optional[str] = Header(None, alias="X-Pyrus-Retry"),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
):
    """
    Обрабатывает входящий POST от Pyrus.
    Проверяет подпись, возвращает 2xx быстро и ставит фоновую задачу для тяжёлой логики.
    """
    body = await request.body()
    data = json.loads(body)

    # data = json.loads(raw_body)
    # print(json.dumps(data, ensure_ascii=False, indent=2))

    # # Проверка User-Agent (рекомендуется)
    # if user_agent and not user_agent.startswith("Pyrus-Bot-"):
    #     logging.warning("Unexpected User-Agent: %s", user_agent)
    #     # не обязательно отклонять — но можно логировать
    #
    # # Проверяем подпись
    # if settings.WEBHOOK_SECURITY_KEY:
    #     print(settings.WEBHOOK_SECURITY_KEY)
    #     if not verify_signature(x_pyrus_sig, raw_body):
    #         logging.warning("Invalid or missing X-Pyrus-Sig header")
    #         raise HTTPException(status_code=403, detail="Invalid signature")

    # Быстрая парсинг/валидация тела
    try:

        event = data.get("event")
        task_id = data.get("task_id")

        cache = await get_cache(task_id)
        if not cache:
            cache = await find_user_id(data)
            await save_cache(task_id, cache, IDEPT_TTL)

        data["user_id"] = cache

    except Exception as exc:
        logging.exception("Invalid payload")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")


    # Логируем попытку (retry)
    logging.info("Received Pyrus webhook: event=%s task_id=%s retry=%s", event, task_id, x_pyrus_retry)

    background_tasks.add_task(process_event, data)

    return JSONResponse(status_code=status.HTTP_200_OK, content={})
