import json
import logging
import re
from aiogram.fsm.context import FSMContext
from typing import List, Dict, Optional

from bot.clients.redis_client import RedisClient

logger = logging.getLogger(__name__)

class TaskUtils:

    @staticmethod
    def extract_task_fields(task: Dict) -> tuple:
        """Извлечение полей задачи с защитой от отсутствия данных"""
        task_data = task.get("task")
        fields = task_data.get("fields", [])
        problem = next((f.get("value") for f in fields if f.get("id") == 1), "Не указано")
        description = next((f.get("value") for f in fields if f.get("id") == 2), "Не указано")
        return problem, description

    @classmethod
    def filter_tasks_by_username(cls, tasks: List[Dict], user_id: int) -> List[Dict]:
        """Фильтрация задач по Telegram username."""
        if not user_id:
            return []

        user_id = str(user_id)

        return [
            task for task in tasks
            if any(
                field.get("code") == "id_user" and
                str(field.get("value", "")) == user_id
                for field in task.get("fields", [])
            )
        ]

    @classmethod
    def extract_data_from_callback(cls, callback_data: str) -> Optional[int]:
        """
        Извлекает ID задачи из callback_data с валидацией
        Примеры форматов:
        - "task_123"
        - "comment_123"
        - "cancel_123"
        """
        try:
            if not callback_data:
                logger.warning("Empty callback_data received")
                return None

            # Используем регулярное выражение для поиска ID
            match = re.search(r'(?:task|comment|cancel|give_mark|grade)_(\d+)$', callback_data)
            if not match:
                logger.warning(f"Invalid callback_data format: {callback_data}")
                return None

            task_id = int(match.group(1))

            # Валидация ID (должен быть положительным числом)
            if task_id <= 0:
                logger.warning(f"Invalid task ID: {task_id}")
                return None

            return task_id

        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"Error extracting task ID from '{callback_data}': {e}")
            return None

    @staticmethod
    async def get_task_id(state: FSMContext) -> Optional[int]:
        """Получение task_id из состояния"""
        data = await state.get_data()
        return data.get("task_id")

    @staticmethod
    def is_data_verification(tasks: list[dict], data: str) -> int | None:
        """Находит ID задачи по значению поля 'Dadata Inn'"""
        for task in tasks:
            for field in task.get("fields", []):
                if field.get("code") == "Dadata Inn" and field.get("value") == data:
                    return task.get("id")
        return None

    @staticmethod
    def find_user_id(tasks: list[dict], user_id: str) -> str | None:
        for task in tasks:
            for field in task.get("fields", []):
                if field.get("code") == "user_id" and field.get("value") == user_id:
                    return task.get("id")
        return None

    @staticmethod
    async def get_tasks_for_user(user_id: int):
        pattern = f"available_task:{user_id}:*"
        redis_client = await RedisClient.get_instance()
        keys = await redis_client.keys(pattern)
        tasks = []
        for key in keys:
            raw = await redis_client.get(key)
            if raw is None:
                continue
            task_data = json.loads(raw)
            tasks.append(task_data)
        return tasks
