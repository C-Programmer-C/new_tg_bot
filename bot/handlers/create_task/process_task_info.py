import logging
from bot.keyboards.create_task import ItemCallback
from bot.keyboards.create_task import CreateTaskKeyboards
from bot.states.create_task import CreateTask
from bot.texts.create_task import CreateTaskMessages
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from bot.utils.validate_text import validate_text
from . import create_task_router
from .post_task_info import create_task_by_api, clear_user_files_from_redis
from ..main_menu.main_menu import return_to_main_menu
from ...keyboards.main_menu import MainMenuKeyboards
from ...texts.task_actions import TaskActionsMessages


@create_task_router.callback_query(CreateTask.choose_theme, F.data == 'themes_to_main_menu')
async def theme_back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    try:
        await return_to_main_menu(callback, state)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in show_tasks: {e}")
        await callback.message.edit_text(
            TaskActionsMessages.SERVER_ERROR_MESSAGE
        )
        await callback.answer()

@create_task_router.callback_query(CreateTask.choose_theme, ItemCallback.filter())
async def choose_theme_task(
        callback: types.CallbackQuery,
        callback_data: ItemCallback, state: FSMContext
):
    user_value = callback_data.item_id
    await state.update_data(theme_id=user_value)
    await state.set_state(CreateTask.input_problem)
    await callback.message.edit_text(CreateTaskMessages.INPUT_PROBLEM_MESSAGE)


@create_task_router.message(CreateTask.input_problem)
async def input_problem(message: types.Message, state: FSMContext):
    problem = message.text
    is_correct = await validate_text(text=problem,
                                     message=message,
                                     on_empty="Пожалуйста введите проблему!",
                                     on_too_short="Слишком короткий текст!",
                                     on_too_long="Слишком длинный текст",
                                     min_length=1, max_length=2000)

    if not is_correct:
        return

    await state.update_data(text_problem=problem)
    await state.set_state(CreateTask.choose_add_files)
    await message.answer(CreateTaskMessages.IS_ATTACH_FILES_MESSAGE, reply_markup=CreateTaskKeyboards.attach_files_keyboard())

@create_task_router.callback_query(CreateTask.choose_add_files, F.data == 'add_files')
async def check_data(event: types.CallbackQuery, state: FSMContext):
    await event.message.edit_text("Пожалуйста, подождите...")
    await event.message.answer(CreateTaskMessages.ADD_FILES_MESSAGE, reply_markup=CreateTaskKeyboards.files_keyboard())
    await state.set_state(CreateTask.add_files)
    await state.update_data(is_processed=False)

@create_task_router.callback_query(CreateTask.choose_add_files, F.data == 'no_files')
async def check_data(event: types.CallbackQuery, state: FSMContext):
    await event.message.edit_text("Пожалуйста, подождите...")
    username = event.from_user.username
    user_id = event.from_user.id
    task_id = await create_task_by_api(state, username, user_id)
    if task_id:
        await clear_user_files_from_redis(user_id)
        await event.message.answer(CreateTaskMessages.format_post_task_message(task_id), reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard())
    else:
        await event.message.answer(CreateTaskMessages.MESSAGE_CREATE_TASK_ERROR, reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard())



