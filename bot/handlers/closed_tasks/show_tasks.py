import asyncio
import json
import logging
from typing import List

from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.clients.redis_client import RedisClient
from bot.handlers.closed_tasks import closed_tasks_router
from aiogram import types, F

from bot.handlers.main_menu.main_menu import return_to_main_menu
from bot.keyboards.closed_tasks import build_closed_tasks_keyboard
from bot.keyboards.main_menu import MainMenuKeyboards
from bot.services.pyrus_api_service import PyrusService
from bot.states.closed_tasks import ClosedTasks
from bot.texts.closed_tasks import ClosedTasksTexts
from bot.texts.task_actions import TaskActionsMessages

logger = logging.getLogger(__name__)

async def check_task_validity(key: str) -> dict | None:
    redis_client = await RedisClient.get_instance()
    raw = await redis_client.get(key)
    if not raw:
        return None

    try:
        data = json.loads(raw)
        task_id = data["task_id"]
        task = await PyrusService.get_task_by_id(int(task_id))
        task_data = task.get("task")
        if not task_data.get("close_date"):  # нет закрытия → задача переоткрыта
            await redis_client.delete(key)
            return None
        return task_data
    except Exception as e:
        logger.warning(f"Ошибка при проверке задачи {key}: {e}")
        return None

async def get_valid_available_tasks(user_id: int) -> List[dict]:
    redis_client = await RedisClient.get_instance()
    keys = await redis_client.keys(f"available_task:{user_id}:*")
    if not keys:
        return []

    tasks = await asyncio.gather(*(check_task_validity(key) for key in keys))
    return [task for task in tasks if task is not None]


@closed_tasks_router.callback_query(ClosedTasks.show_closed_tasks, F.data == 'closed_tasks_back_to_menu')
async def transition_back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    try:
        await return_to_main_menu(callback, state)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in show_tasks: {e}")
        await callback.message.edit_text(
            TaskActionsMessages.SERVER_ERROR_MESSAGE
        )
        await callback.answer()

@closed_tasks_router.callback_query(StateFilter(None), F.data == 'closed_tasks')
async def show_closed_tasks(event: types.CallbackQuery, state: FSMContext):
    user_id = event.from_user.id
    await state.set_state(ClosedTasks.show_closed_tasks)
    tasks = await get_valid_available_tasks(user_id)
    if not tasks:
        await event.message.edit_text(ClosedTasksTexts.NOT_FOUND_CLOSED_TASKS_TEXT, reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard())
        return
    keyboard = build_closed_tasks_keyboard(tasks)
    await event.message.edit_text(
        ClosedTasksTexts.CLOSED_TASKS_TEXT,
        reply_markup=keyboard
    )

