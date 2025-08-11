import logging
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.handlers.closed_tasks import closed_tasks_router
from aiogram import types, F
from bot.handlers.main_menu.main_menu import return_to_main_menu
from bot.keyboards.main_menu import MainMenuKeyboards
from bot.services.pyrus_api_service import PyrusService
from bot.states.closed_tasks import ClosedTasks
from bot.texts.closed_tasks import ClosedTasksTexts
from bot.texts.task_actions import TaskActionsMessages
from bot.utils.task_utils import TaskUtils


@closed_tasks_router.callback_query(ClosedTasks.show_closed_task_info, F.data == 'show_closed_task_info_back_to_menu')
async def show_closed_task_info_back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    try:
        await return_to_main_menu(callback, state)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in show_tasks: {e}")
        await callback.message.edit_text(
            TaskActionsMessages.SERVER_ERROR_MESSAGE
        )
        await callback.answer()


@closed_tasks_router.callback_query(ClosedTasks.show_closed_tasks, lambda c: c.data.startswith("closed_task_"))
async def task_detail(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ClosedTasks.show_closed_task_info)
    task_id = int(callback.data.split("_")[2])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ClosedTasksTexts.OPEN_TASK_TEXT, callback_data=f"open_{task_id}")],
        [InlineKeyboardButton(text=ClosedTasksTexts.MAIN_MENU_TEXT, callback_data="show_closed_task_info_back_to_menu")]
    ])

    task = await PyrusService.get_task_by_id(task_id)
    if not task:
        await callback.message.edit_text(
            TaskActionsMessages.TASK_ERROR_MESSAGE,
            reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
        )
        return
    problem, description = TaskUtils.extract_task_fields(task)
    message = TaskActionsMessages.get_task_data_message(task_id, problem, description)
    await callback.message.edit_text(message, reply_markup=keyboard, parse_mode="HTML")