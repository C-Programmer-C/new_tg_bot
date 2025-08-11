import logging
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.clients.redis_client import RedisClient
from bot.handlers.closed_tasks import closed_tasks_router
from bot.handlers.main_menu.main_menu import return_to_main_menu
from bot.services.api_client import open_task_by_api
from bot.states.closed_tasks import ClosedTasks
from bot.texts.closed_tasks import ClosedTasksTexts
from bot.texts.task_actions import TaskActionsMessages


@closed_tasks_router.callback_query(ClosedTasks.open_task, F.data == 'open_task_back_to_main_menu')
async def open_task_back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    try:
        await return_to_main_menu(callback, state)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in show_tasks: {e}")
        await callback.message.edit_text(
            TaskActionsMessages.SERVER_ERROR_MESSAGE
        )
        await callback.answer()

@closed_tasks_router.callback_query(ClosedTasks.show_closed_task_info, lambda c: c.data.startswith("open_"))
async def open_task_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ClosedTasks.open_task)
    task_id = int(callback.data.split("_")[1])
    redis_client = await RedisClient.get_instance()
    success = await open_task_by_api(task_id, comment_text=ClosedTasksTexts.USER_OPEN_TASK)
    user_id = callback.from_user.id
    if not success:
        await callback.answer(ClosedTasksTexts.ERROR_OPEN_TASK_TEXT, show_alert=True)
        return
    await redis_client.delete(f"available_task:{user_id}:{task_id}")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ClosedTasksTexts.MAIN_MENU_TEXT, callback_data="open_task_back_to_main_menu")],
    ])

    await callback.message.edit_text(ClosedTasksTexts.SUCCESS_OPEN_TASK, reply_markup=keyboard)
