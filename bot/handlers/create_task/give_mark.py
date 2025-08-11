import datetime

from aiogram.filters import StateFilter
import logging
from aiogram.fsm.context import FSMContext
from aiogram import types, F
from bot.keyboards.main_menu import MainMenuKeyboards
from bot.states.create_task import CreateTask
from bot.texts.create_task import CreateTaskMessages
from bot.texts.task_actions import TaskActionsMessages
from bot.services.pyrus_api_service import PyrusService
from . import create_task_router
from bot.keyboards.create_task import CreateTaskKeyboards
from ..main_menu.main_menu import return_to_main_menu
from ...utils.task_utils import TaskUtils

logger = logging.getLogger(__name__)

@create_task_router.callback_query(CreateTask.choose_mark, F.data == 'mark_back_to_main_menu')
async def get_main_menu(callback: types.CallbackQuery, state: FSMContext):
    try:
        await return_to_main_menu(callback, state)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in show_tasks: {(str(e))}")
        await callback.message.edit_text(
            TaskActionsMessages.SERVER_ERROR_MESSAGE
        )
        await callback.answer()

@create_task_router.callback_query(CreateTask.give_mark, F.data == 'get_main_menu')
async def back_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    try:
        await return_to_main_menu(callback, state)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in show_tasks: {(str(e))}")
        await callback.message.edit_text(
            TaskActionsMessages.SERVER_ERROR_MESSAGE
        )
        await callback.answer()

@create_task_router.callback_query(StateFilter(None), F.data.startswith("give_mark_"))
async def choose_mark(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(CreateTask.give_mark)
    task_id = TaskUtils.extract_data_from_callback(callback.data)
    if not task_id:
        logger.error(f"Invalid task ID in callback: {callback.data}")
        await callback.message.edit_text(
            TaskActionsMessages.SERVER_ERROR_MESSAGE,
            reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
        )
        return
    await state.update_data(current_task_id=task_id)
    await callback.message.edit_text(CreateTaskMessages.CHECK_QUALITY_MESSAGE, reply_markup=CreateTaskKeyboards.service_rating_keyboard())



@create_task_router.callback_query(CreateTask.give_mark, F.data.startswith("grade_"))
async def process_service_rating(
    callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор оценки от 1 до 5"""
    await state.set_state(CreateTask.choose_mark)
    data = callback.data
    mark = TaskUtils.extract_data_from_callback(data)
    if not mark:
        await callback.message.edit_text("Произошла ошибка попробуйте позже...", show_alert=True)
        return
    data = await state.get_data()
    task_id = data['current_task_id']
    if not task_id:
        logger.error(f"Invalid task ID in callback: {callback.data}")
        await callback.message.edit_text(
            TaskActionsMessages.SERVER_ERROR_MESSAGE,
            reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
        )
        return
    task_id = int(task_id)
    mark = int(mark)
    await PyrusService.open_task(task_id)
    json_data = {
        "field_updates": [
            {
                "id": 15,
                "value": {"choice_id": mark},
            },

            {"id": 17, "value": datetime.date.today().isoformat()},
        ]
    }
    success = await PyrusService.post_comment_value_fields(task_id, json_data)
    if not success:
        logger.error(f"Invalid task ID in callback: {callback.data}")
        await callback.message.edit_text(
            TaskActionsMessages.SERVER_ERROR_MESSAGE,
            reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
        )
        return
    await PyrusService.close_task(task_id)
    logging.info(f"User {callback.from_user.id} gave task with id: {task_id} rating: {mark}")

    await callback.message.edit_text(CreateTaskMessages.set_mark_message(mark), reply_markup=CreateTaskKeyboards.back_to_main_menu(), parse_mode="HTML")
