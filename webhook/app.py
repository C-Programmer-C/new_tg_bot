import hashlib
import os
import logging
from typing import Optional, List, Dict, Any, Coroutine
from fastapi import FastAPI, Request, Header, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from bot.clients.redis_client import RedisClient
from config import settings
from webhook.signature_verification import verify_signature
from redis.exceptions import RedisError
import time

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Pyrus Webhook (FastAPI + Redis idempotency)")
IDEPT_TTL = int(os.getenv("PYRUS_IDEMPOTENT_TTL", str(60 * 60)))


if not settings.WEBHOOK_SECURITY_KEY:
    logging.warning("PYRUS_BOT_SECRET is not set — signature verification will fail.")


# --- Простые модели для валидации (убраны лишние поля, можно расширить) ---
class Person(BaseModel):
    id: int
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]


class Comment(BaseModel):
    id: Optional[int]
    create_date: Optional[str]
    text: Optional[str]
    author: Optional[Person]


class TaskModel(BaseModel):
    text: Optional[str]
    id: int
    create_date: Optional[str]
    last_modified_date: Optional[str]
    author: Optional[Person]
    responsible: Optional[Person]
    participants: Optional[List[Person]] = []
    comments: Optional[List[Comment]] = []


class PyrusEvent(BaseModel):
    event: str
    access_token: Optional[str]
    task_id: int
    user_id: Optional[int]
    task: TaskModel

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


# --- Обработка события (долго) ---
async def process_event_long(event: PyrusEvent):
    """
    Тяжёлая обработка — например: логика, вызов внешних сервисов, запись в БД, или добавление комментария через API.
    Это выполняется в BackgroundTasks, чтобы основной эндпоинт вернул 2xx быстро.
    """
    logging.info(f"Background processing for task_id={event.task_id}, event={event.event}")

    pass


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
    raw_body = await request.body()

    # Проверка User-Agent (рекомендуется)
    if user_agent and not user_agent.startswith("Pyrus-Bot-"):
        logging.warning("Unexpected User-Agent: %s", user_agent)
        # не обязательно отклонять — но можно логировать

    # Проверяем подпись
    if settings.WEBHOOK_SECURITY_KEY:
        print(settings.WEBHOOK_SECURITY_KEY)
        if not verify_signature(x_pyrus_sig, raw_body):
            logging.warning("Invalid or missing X-Pyrus-Sig header")
            raise HTTPException(status_code=403, detail="Invalid signature")

    # Быстрая парсинг/валидация тела
    try:
        payload = await request.json()
        event = PyrusEvent.model_validate(payload)
    except Exception as exc:
        logging.exception("Invalid payload")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Логируем попытку (retry)
    logging.info("Received Pyrus webhook: event=%s task_id=%s retry=%s", event.event, event.task_id, x_pyrus_retry)

    # Идемпотентность: используем комбинацию event+task_id+maybe last comment id
    # event_key = f"{event.event}:{event.task_id}:{event.task.last_modified_date or ''}"

    # is_new = await remember_event(event_key)

    # if is_new is None:
    #     logging.info("Duplicate event detected, skipping heavy processing.")
    #     raise HTTPException(status_code=503, detail="Redis unavailable")
    #
    # if is_new is False:
    #     return JSONResponse(status_code=200, content={"result": "duplicate"})

    # Добавляем фоновую обработку
    background_tasks.add_task(process_event_long, event)

    # Быстрый ответ 200: можно сразу вернуть комментарии, если нужно.
    # Формат ответа: Pyrus принимает JSON с полем "comments" (см. документацию).
    # Здесь пример простого автоматического комментария, который Pyrus добавит в задачу.
    response_payload = {
        "result": "accepted",
        # Пример: Pyrus позволяет добавить комментарий в теле ответа -> формат зависит от вашей версии API.
        # Поле ниже — пример, при желании можно удалить и сделать добавление асинхронно через API.
        "comments": [
            {
                "text": "Принял, обрабатываю автоматически (бот).",
                # "author_id": <id>  # обычно не требуется, т.к. коммент добавляется от бота
            }
        ],
    }

    return None
