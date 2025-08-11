from aiogram.filters import StateFilter

from bot.clients.redis_client import RedisClient
from bot.texts.create_task import CreateTaskMessages
from bot.utils.task_utils import TaskUtils
from bot.services.pyrus_api_service import PyrusService
from bot.keyboards.create_task import CreateTaskKeyboards
import logging
from aiogram.fsm.context import FSMContext
from aiogram import types, F
from bot.keyboards.main_menu import MainMenuKeyboards
from bot.states.create_task import CreateTask
from bot.texts.task_actions import TaskActionsMessages
from bot.utils.validate_text import validate_text
from . import create_task_router
from ..main_menu.main_menu import return_to_main_menu

MIN_INN_LENGTH = 6
MAX_INN_LENGTH = 12

@create_task_router.callback_query(StateFilter(None), F.data == 'data_again_back_to_main_menu')
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


async def process_identity_number(
        identity_number: str,
        user_id: str,
        state: FSMContext,
        message: types.Message,
        is_answer_message: bool = False
) -> bool:
    """
    Обрабатывает ИНН: проверяет, ищет подрядчика и пользователя
    Возвращает True если данные валидны, иначе False
    """

    # Проверка ИНН
    if not identity_number:
        await message.edit_text(CreateTaskMessages.INPUT_DATA_MESSAGE)
        await state.set_state(CreateTask.input_identity_number)
        return False

    # Получение и проверка подрядчиков
    contractors = await PyrusService.get_contractors()
    contractor_id = TaskUtils.is_data_verification(contractors, identity_number)

    if not contractor_id:
        if is_answer_message:
            await message.answer(
                CreateTaskMessages.NOT_FOUND_DATA_MESSAGE,
                reply_markup=CreateTaskKeyboards.input_data_again_keyboard()
            )
        else:
            await message.edit_text(
                CreateTaskMessages.NOT_FOUND_DATA_MESSAGE,
                reply_markup=CreateTaskKeyboards.input_data_again_keyboard()
            )
        await delete_identity_number(user_id)
        return False

    await save_identity_number(user_id, identity_number)

    # Обновление состояния
    await state.update_data(
        contractor_id=contractor_id
    )

    # Поиск пользователя
    users = await PyrusService.get_users()
    task_id = TaskUtils.find_user_id(users, user_id)

    if task_id:
        await state.update_data(user_task_id=task_id)
        return True

    if is_answer_message:
        await message.answer(
            CreateTaskMessages.INPUT_USER_DATA,
            reply_markup=CreateTaskKeyboards.transition_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.edit_text(
            CreateTaskMessages.INPUT_USER_DATA,
            reply_markup=CreateTaskKeyboards.transition_keyboard(),
            parse_mode="HTML"
        )
    await state.set_state(CreateTask.input_user_data)
    return False


async def handle_verified_identity(message: types.Message, state: FSMContext, is_answer_message: bool = False):
    """Обрабатывает действия после успешной верификации ИНН"""
    items = await PyrusService.get_items()
    keyboard = await CreateTaskKeyboards.build_themes_task_keyboard(items)
    await state.set_state(CreateTask.choose_theme)
    if not is_answer_message:
        await message.answer(
        CreateTaskMessages.CHOOSE_THEME_TASK_MESSAGE,
        reply_markup=keyboard
        )
    else:
        await message.edit_text(
        CreateTaskMessages.CHOOSE_THEME_TASK_MESSAGE,
        reply_markup=keyboard
        )

async def delete_identity_number(user_id: str) -> None:
    redis = await RedisClient.get_instance()
    redis_key = f"inn:{user_id}"
    await redis.delete(redis_key)

async def get_identity_number(user_id: str):
    redis = await RedisClient.get_instance()
    redis_key = f"inn:{user_id}"
    inn = await redis.get(redis_key)
    return inn or None

@create_task_router.callback_query(StateFilter(None), F.data == 'process_data')
async def check_data(event: types.CallbackQuery, state: FSMContext):
    """Обработчик проверки данных по callback"""
    try:
        await state.set_state(CreateTask.check_data)

        user_id = str(event.from_user.id)
        if not user_id:
            raise ValueError("User ID not found") # сделать

        identity_number = await get_identity_number(user_id)

        if await process_identity_number(identity_number, user_id, state, event.message):
            await handle_verified_identity(event.message, state, is_answer_message=True)

        await event.answer()

    except Exception as e:
        logging.exception(f"Ошибка при обработке данных {e}")
        await event.message.answer(
            TaskActionsMessages.SERVER_ERROR_MESSAGE,
            reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
        )

async def save_identity_number(user_id: str, inn: str) -> None:
    redis = await RedisClient.get_instance()
    redis_key = f"inn:{user_id}"
    await redis.set(redis_key, inn)

@create_task_router.message(CreateTask.input_identity_number)
async def input_data(message: types.Message, state: FSMContext):
    """Обработчик ввода ИНН"""
    try:
        input_text = message.text

        # Валидация текста
        is_correct = await validate_text(
            text=input_text,
            message=message,
            on_empty=CreateTaskMessages.INN_EMPTY_MESSAGE,
            on_too_short=CreateTaskMessages.INN_SHORT_MESSAGE,
            on_too_long=CreateTaskMessages.INN_LONG_MESSAGE,
            min_length=MIN_INN_LENGTH,
            max_length=MAX_INN_LENGTH
        )
        if not is_correct:
            return

        user_id = str(message.from_user.id)

        await state.clear()

        await message.answer(CreateTaskMessages.CHECK_INN_MESSAGE)

        if await process_identity_number(input_text, user_id, state, message, True):
            await handle_verified_identity(message, state)

    except Exception:
        logging.exception("Ошибка при обработке ИНН")
        await message.answer(
            TaskActionsMessages.SERVER_ERROR_MESSAGE,
            reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
        )