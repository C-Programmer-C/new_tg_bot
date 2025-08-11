import re
from aiogram.enums import ParseMode
from bot.utils.validate_text import validate_text
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


@create_task_router.callback_query(CreateTask.input_user_data, F.data == 'transition_back_to_menu')
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

@create_task_router.callback_query(CreateTask.input_user_data, F.data == 'input_fullname')
async def input_fullname(event: types.CallbackQuery, state: FSMContext):
    try:
        await state.set_state(CreateTask.input_Fullname)
        await event.message.edit_text(CreateTaskMessages.INPUT_FULLNAME_MESSAGE)
        await event.answer()
    except Exception:
        logging.exception("Произошла ошибка при отображении информации о задаче и возможных действиях с ней")
        await event.message.answer(TaskActionsMessages.SERVER_ERROR_MESSAGE, reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard())
        await event.answer()

@create_task_router.message(CreateTask.input_Fullname)
async def process_fullname(message: types.Message, state: FSMContext):
    try:
        fullname = message.text
        is_correct = await validate_text(text=fullname, message=message, on_empty="Пожалуйста введите ФИО!", on_too_short="Слишком короткий текст!", on_too_long="Слишком длинный текст", min_length=3, max_length=150)

        if not is_correct:
            return

        await state.update_data(fullname=fullname)
        await message.answer(CreateTaskMessages.PHONE_INPUT_MESSAGE)
        await state.set_state(CreateTask.input_telephone)
    except Exception:
        logging.exception("Произошла ошибка при обработке введенного ФИО пользователя.")
        await message.answer(TaskActionsMessages.SERVER_ERROR_MESSAGE, reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard())


@create_task_router.message(CreateTask.input_telephone)
async def process_telephone(message: types.Message, state: FSMContext):
    try:
        phone = message.text.strip()
        if not phone:
            await message.answer(CreateTaskMessages.MESSAGE_PHONE_EMPTY)
            return

        # Очищаем номер от всех нецифровых символов
        phone_clean = re.sub(r'\D', '', phone)
        # Проверяем длину номера
        if len(phone_clean) < 10:
            await message.answer(CreateTaskMessages.MESSAGE_PHONE_TOO_SHORT)
            return
        elif len(phone_clean) > 11:
            await message.answer(CreateTaskMessages.MESSAGE_PHONE_TOO_LONG)
            return

        # Если 10 цифр — считаем, что это номер без кода страны, добавляем 7
        if len(phone_clean) == 10:
            normalized_phone = '7' + phone_clean
        elif len(phone_clean) == 11:
            # Проверяем, что номер начинается с 7 или 8
            if phone_clean[0] not in ('7', '8'):
                await message.answer(CreateTaskMessages.MESSAGE_PHONE_INVALID_START)
                return
            # Нормализуем номер — заменяем первый символ на 7 для единообразия
            normalized_phone = '7' + phone_clean[1:]
        else:
            await message.answer(CreateTaskMessages.MESSAGE_PHONE_INVALID_FORMAT)
            return

        # Сохраняем нормализованный номер в состоянии
        await state.update_data(telephone_number=normalized_phone)
        await message.answer(CreateTaskMessages.INPUT_NAME_PC_MESSAGE,  parse_mode=ParseMode.HTML)
        await state.set_state(CreateTask.input_pc_name)

    except Exception:
        logging.exception("Произошла ошибка при обработке номера телефона")
        await message.answer(TaskActionsMessages.SERVER_ERROR_MESSAGE,
                             reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard())


@create_task_router.message(CreateTask.input_pc_name)
async def process_pc_name(message: types.Message, state: FSMContext):
    pc_name = message.text
    is_correct = await validate_text(text=pc_name,
                                     message=message,
                                     on_empty=CreateTaskMessages.MESSAGE_PC_NAME_EMPTY,
                                     on_too_short=CreateTaskMessages.MESSAGE_PC_NAME_TOO_SHORT,
                                     on_too_long=CreateTaskMessages.MESSAGE_PC_NAME_TOO_LONG,
                                     min_length=1,
                                     max_length=150)
    if not is_correct:
        return
    await state.update_data(pc_name=pc_name)
    items = await PyrusService.get_items()
    keyboard = await CreateTaskKeyboards.build_themes_task_keyboard(items)
    await state.set_state(CreateTask.choose_theme)
    await message.answer(CreateTaskMessages.CHOOSE_THEME_TASK_MESSAGE, reply_markup=keyboard)