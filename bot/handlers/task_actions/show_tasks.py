import logging

from aiogram import types, F
from aiogram.utils.markdown import html_decoration as hd
from aiogram.fsm.context import FSMContext
from bot.services.pyrus_api_service import PyrusService
from bot.keyboards.main_menu import MainMenuKeyboards
from bot.keyboards.task_actions import TaskActionsKeyboards
from bot.texts.task_actions import TaskActionsMessages
from bot.utils.task_utils import TaskUtils
from . import task_actions_router
from aiogram.filters import StateFilter

from ..main_menu.main_menu import return_to_main_menu
from ...states.add_comment import AddComment

logger = logging.getLogger(__name__)


@task_actions_router.callback_query(F.data == 'back_to_main_menu')
async def back_to_main_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    try:
        await return_to_main_menu(callback, state)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in show_tasks: {hd.quote(str(e))}")
        await callback.message.edit_text(
            TaskActionsMessages.SERVER_ERROR_MESSAGE
        )
        await callback.answer()


@task_actions_router.callback_query(StateFilter(None), F.data == 'tasks')
async def start_show_tasks_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик для показа задач пользователя."""
    try:
        await state.set_state(AddComment.choose_task)
        # Проверка username
        if not callback.from_user.username:
            await callback.message.edit_text(
                TaskActionsMessages.NOT_FOUND_USERNAME_MESSAGE,
                reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
            )
            await callback.answer()
            return

        # Получение и фильтрация задач
        all_tasks = await PyrusService.get_tasks()
        user_tasks = TaskUtils.filter_tasks_by_username(
            all_tasks,
            callback.from_user.id
        )

        # Обработка случаев
        if not user_tasks:
            await state.clear()
            await callback.message.edit_text(
                TaskActionsMessages.NOT_FOUND_TASKS_MESSAGE,
                reply_markup=TaskActionsKeyboards.create_empty_tasks_keyboard()
            )
        else:
            await callback.message.edit_text(
                TaskActionsMessages.SHOW_TASKS_MESSAGE,
                reply_markup=TaskActionsKeyboards.create_task_keyboard(user_tasks)
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in show_tasks: {hd.quote(str(e))}")
        await callback.message.edit_text(
            TaskActionsMessages.SERVER_ERROR_MESSAGE
        )
        await callback.answer()