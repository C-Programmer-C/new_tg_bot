import logging
from aiogram import types, F
from aiogram.fsm.context import FSMContext

from bot.services.pyrus_api_service import PyrusService
from bot.texts.task_actions import TaskActionsMessages
from bot.keyboards.main_menu import MainMenuKeyboards
from bot.utils.task_utils import TaskUtils
from . import task_actions_router
from ..main_menu.main_menu import return_to_main_menu
from ...states.add_comment import AddComment

logger = logging.getLogger(__name__)



@task_actions_router.callback_query(AddComment.close_task, F.data == 'closed_tasks_back_to_menu')
async def back_to_main_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    try:
        await return_to_main_menu(callback, state)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in show_tasks: {e}")
        await callback.message.edit_text(
            TaskActionsMessages.SERVER_ERROR_MESSAGE
        )
        await callback.answer()

@task_actions_router.callback_query(AddComment.show_task_info, F.data.startswith("cancel_"))
async def handle_close_task(
    callback: types.CallbackQuery,
    state: FSMContext
):
    """Обработчик закрытия задачи"""
    try:

        await state.set_state(AddComment.close_task)
        task_id = TaskUtils.extract_data_from_callback(callback.data)
        if not task_id:
            logger.error(f"Invalid task ID in callback: {callback.data}")
            await callback.message.edit_text(
                TaskActionsMessages.SERVER_ERROR_MESSAGE,
                reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
            )
            return

        if await PyrusService.close_task(task_id, TaskActionsMessages.USER_CLOSE_TASK_TEXT):
            await callback.message.edit_text(
                TaskActionsMessages.CLOSE_TASK_TEXT,
                reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
            )
        else:
            await callback.message.edit_text(
                TaskActionsMessages.CLOSE_FAILED,
                reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
            )

    except Exception as e:
        logger.exception(f"Error processing task close: {str(e)}")
        await callback.message.edit_text(
            TaskActionsMessages.SERVER_ERROR_MESSAGE,
            reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
        )
    finally:
        await callback.answer()