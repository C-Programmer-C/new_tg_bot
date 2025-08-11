import logging

import aiohttp

from bot.services.pyrus_api_service import PyrusService

API_BASE_URL = "http://localhost:8000"

async def fetch_active_tasks():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/tasks/") as resp:
            return await resp.json()

async def close_task(task_id: int):
    async with aiohttp.ClientSession() as session:
        data = {"text": "It's done.", "action": "reopened"}
        async with session.post(f"{API_BASE_URL}/tasks/{task_id}/open", json=data) as resp:
            return await resp.json()

async def open_task_by_api(task_id: int, comment_text: str, action: str = "reopened") -> bool:
    """
    Отправляет POST запрос к API для открытия задачи.
    Возвращает True если успешно, False иначе.
    """
    success = await PyrusService.open_task(task_id, comment_text)
    if not success:
        logging.error("Произошла ошибка при открытии задачи")
        return False
    else:
        return True

