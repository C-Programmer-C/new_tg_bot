from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import html_decoration as hd
from bot.services.pyrus_api_service import PyrusService
from bot.keyboards.main_menu import MainMenuKeyboards
from bot.keyboards.task_actions import TaskActionsKeyboards
from bot.texts.task_actions import TaskActionsMessages
from . import task_actions_router
import logging
from bot.handlers.task_actions.show_tasks import start_show_tasks_handler
from ..main_menu.main_menu import return_to_main_menu
from ...states.add_comment import AddComment
from ...utils.task_utils import TaskUtils

logger = logging.getLogger(__name__)


@task_actions_router.callback_query(AddComment.show_task_info, F.data == 'show_tasks')
async def back_to_show_tasks_handler(callback: types.CallbackQuery, state: FSMContext):
    try:
        await start_show_tasks_handler(callback, state)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in show_tasks: {hd.quote(str(e))}")
        await callback.message.edit_text(
            TaskActionsMessages.SERVER_ERROR_MESSAGE
        )
        await callback.answer()

@task_actions_router.callback_query(AddComment.show_task_info, F.data == 'back_to_main_menu')
async def show_tasks_handler(callback: types.CallbackQuery, state: FSMContext):
    try:
        await return_to_main_menu(callback, state)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in show_tasks: {hd.quote(str(e))}")
        await callback.message.edit_text(
            TaskActionsMessages.SERVER_ERROR_MESSAGE
        )
        await callback.answer()

@task_actions_router.callback_query(AddComment.choose_task, F.data.startswith("task_"))
async def show_task_info_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик для отображения информации о задаче"""
    try:


        await state.set_state(AddComment.show_task_info)

        data = await state.get_data()

        task_id = data.get("task_id")
        if not task_id:
            # Извлечение ID задачи
            task_id = TaskUtils.extract_data_from_callback(callback.data)
            if not task_id:
                logger.error(f"Invalid task ID in callback: {callback.data}")
                await callback.message.edit_text(
                    TaskActionsMessages.SERVER_ERROR_MESSAGE,
                    reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
                )
                return
            await state.update_data(task_id=task_id)

        # Получение задачи
        task = await PyrusService.get_task_by_id(task_id)
        if not task:
            await callback.message.edit_text(
                TaskActionsMessages.TASK_ERROR_MESSAGE,
                reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
            )
            return

        # Формирование сообщения
        problem, description = TaskUtils.extract_task_fields(task)
        message = TaskActionsMessages.get_task_data_message(task_id, problem, description)

        await callback.message.edit_text(
            message,
            reply_markup=TaskActionsKeyboards.create_actions_keyboard(task_id),
            parse_mode="HTML"
        )
        await callback.answer()

    except Exception as e:
        logger.exception(f"Error showing task info: {hd.quote(str(e))}")
        await callback.message.edit_text(
            TaskActionsMessages.SERVER_ERROR_MESSAGE,
            reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
        )
        await callback.answer()