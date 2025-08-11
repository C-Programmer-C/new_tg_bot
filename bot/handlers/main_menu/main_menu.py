import asyncio
import logging
from logging import exception
from aiogram.types import ReplyKeyboardRemove
from aiogram.exceptions import *
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from aiogram import types, F
from aiogram.utils.markdown import html_decoration as hd
from bot.keyboards.main_menu import MainMenuKeyboards
from bot.texts.main_menu import MainMenuMessages
from bot.texts.task_actions import TaskActionsMessages
from . import start_router
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramNotFound,
    TelegramRetryAfter,
    TelegramNetworkError,
)

from ...clients.redis_client import RedisClient
from ...texts.create_task import CreateTaskMessages
from ...utils.check_cooldown import check_cooldown
from ...utils.delete_keys_from_redis import delete_keys_by_pattern_async

logger = logging.getLogger(__name__)


async def _handle_error(event: types.Message | types.CallbackQuery, exception: Exception, error_msg: str):
    logger.exception(error_msg)

    message = event.message if isinstance(event, types.CallbackQuery) else event

    if isinstance(exception, TelegramBadRequest):
        # возможно, ты сюда передашь cleanup через декоратор
        await message.answer("Произошла ошибка при выполнении задачи.")
    elif isinstance(exception, asyncio.TimeoutError):
        await message.answer("Превышено время ожидания ответа сервера.")
    else:
        await message.answer(TaskActionsMessages.SERVER_ERROR_MESSAGE)

@start_router.message(StateFilter(None), Command('start'))
async def send_main_menu(message: types.Message, state: FSMContext):
    """Обработчик команды /start, показывает главное меню."""
    try:
        await state.clear()
        await message.answer(
            MainMenuMessages.WELCOME_MESSAGE,
            reply_markup=MainMenuKeyboards.create_main_menu_keyboard()
        )
    except Exception as e:
        await _handle_error(message, f"Ошибка при показе главного меню: {hd.quote(str(e))}")

@start_router.callback_query(F.data == 'closed_tasks_back_to_menu')
async def return_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    try:
        await state.clear()  # Полная очистка состояния
        await callback.message.edit_text(
            MainMenuMessages.WELCOME_MESSAGE,
            reply_markup=MainMenuKeyboards.create_main_menu_keyboard()
        )
        await callback.answer()
    except Exception as e:
        await _handle_error(callback, f"Ошибка при возврате в главное меню: {hd.quote(str(e))}")

@start_router.message(StateFilter(None), Command('help'))
async def answer_help_info(message: types.Message):
    """Показывает пользователю помощь в работе с ботом"""
    try:
        await message.answer(MainMenuMessages.HELP_MESSAGE)
    except Exception as e:
        await _handle_error(message, f"Ошибка при возврате в главное меню: {hd.quote(str(e))}")

@start_router.message(Command('cancel'))
async def clear_info(message: types.Message, state: FSMContext):
    """Прерывает активный процесс, если он есть, и возвращает пользователя в главное меню."""
    try:
        redis = await RedisClient.get_instance()
        user_id = message.from_user.id
        cooldown_key = f"clear_info_cooldown:{user_id}"

        if not await check_cooldown(redis, cooldown_key):
            await message.answer(MainMenuMessages.COOLDOWN_MESSAGE)
            return

        current_state = await state.get_state()
        if not current_state:
            return  # Ничего не делаем, если пользователь не в состоянии

        await message.answer(TaskActionsMessages.RETURN_TO_MAIN_MENU, reply_markup=ReplyKeyboardRemove())

        await state.clear()

        # Удаляем временные ключи
        await delete_keys_by_pattern_async(redis, f"create_task_file_{user_id}_*")
        await delete_keys_by_pattern_async(redis, f"file_{user_id}_*")

        await message.answer(
            MainMenuMessages.COMMAND_CANCEL_TEXT, reply_markup=MainMenuKeyboards.create_main_menu_keyboard()
        )
    except Exception as e:
        await _handle_error(message, e, f"Ошибка при возврате в главное меню: {hd.quote(str(e))}")

@start_router.callback_query(StateFilter(None), F.data == 'company_info')
async def get_company_info(callback: types.CallbackQuery):
    """Показывает информацию о компании."""
    try:
        await callback.message.edit_text(
            MainMenuMessages.COMPANY_INFO_MESSAGE,
            reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
        )
        await callback.answer()
    except Exception as e:
        await _handle_error(callback, f"Ошибка при показе информации о компании: {hd.quote(str(e))}")


@start_router.callback_query(StateFilter(None), F.data == 'contacts_info')
async def get_feedback_info(callback: types.CallbackQuery):
    """Показывает информацию для обратной связи."""
    try:
        await callback.message.edit_text(
            MainMenuMessages.FEEDBACK_INFO_MESSAGE,
            reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
        )
        await callback.answer()
    except Exception as e:
        await _handle_error(callback, f"Ошибка при показе информации об обратной связи: {hd.quote(str(e))}")