import asyncio
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from bot.clients.bot_client import BotClient
from bot.clients.redis_client import RedisClient
from bot.services.file_service import FileService
from bot.services.pyrus_api_service import PyrusService
from bot.texts.task_actions import TaskActionsMessages
from bot.keyboards.main_menu import MainMenuKeyboards
from bot.utils.get_item_by_value import get_value_by_item_id
from . import create_task_router
import logging
from aiogram.types import ReplyKeyboardRemove
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

from config import settings
from ...states.create_task import CreateTask
from ...texts.create_task import CreateTaskMessages

logger = logging.getLogger(__name__)


@create_task_router.message(CreateTask.add_files, F.text == "Отправить")
async def handle_post_comment(message: types.Message, state: FSMContext):
    """Обработчик отправки комментария с прикрепленными файлами"""
    try:
        user_id = message.from_user.id
        username = message.from_user.username

        # Проверяем, идет ли еще обработка файлов
        if await is_media_processing(user_id):
            await message.answer(CreateTaskMessages.MESSAGE_WAIT_PROCESS_FILES)
            return

        # Получаем файлы из Redis
        files = await get_user_files_from_redis(user_id)
        if not files:
            await message.answer(CreateTaskMessages.MESSAGE_NOT_FILES_FOR_CREATE_TASK)
            return

        await message.answer(CreateTaskMessages.MESSAGE_WAIT_CREATE_TASK,
                            reply_markup=ReplyKeyboardRemove())

        # Подготавливаем файлы для Pyrus
        file_attachments = await prepare_file_attachments(files)


        if not file_attachments:
            await message.answer(CreateTaskMessages.MESSAGE_ERROR_PROCESS_FILES)
            return

        redis = await RedisClient.get_instance()
        processing_key = f"media_processing:{message.from_user.id}"
        await redis.delete(processing_key)

        task_id = await create_task_by_api(state, username, user_id, file_attachments)

        if task_id:
            await clear_user_files_from_redis(user_id)
            await message.answer(CreateTaskMessages.format_post_task_message(task_id), reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard())
        else:
            await message.answer(CreateTaskMessages.MESSAGE_CREATE_TASK_ERROR, reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard())

            # Очищаем состояние
            await state.clear()

    except Exception as e:
        logger.exception(f"Failed to post comment: {e}")
        await message.answer(
            TaskActionsMessages.SERVER_ERROR_MESSAGE,
            reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
        )

async def clear_user_files_from_redis(user_id: int):
    redis = await RedisClient.get_instance()
    file_keys = await redis.keys(f"file_{user_id}_*")
    await asyncio.gather(*(redis.delete(key) for key in file_keys))

async def is_media_processing(user_id: int) -> bool:
    """Проверяет, идет ли обработка медиафайлов для пользователя"""
    redis = await RedisClient.get_instance()
    processing_key = f"media_processing:{user_id}"
    if await redis.exists(processing_key):
        count = int(await redis.get(processing_key))
        return count > 0
    return False


async def get_user_files_from_redis(user_id: int) -> List[Dict]:
    """Получает файлы пользователя из Redis"""
    redis = await RedisClient.get_instance()
    file_keys = await redis.keys(f"create_task_file_{user_id}_*")

    files = []
    for key in file_keys:
        if not await redis.exists(key):
            continue

        file_data = await redis.hgetall(key)
        files.append({
            "file_id": file_data.get("file_id"),
            "filename": file_data.get("filename")
        })

    return files




async def prepare_file_attachments(files: List[Dict]) -> Optional[List]:
    """Подготавливает файлы для отправки в Pyrus"""
    if not files:
        return None

    bot = BotClient.get_instance()
    return await FileService.prepare_files(files=files, bot=bot)



async def extract_user_info(task):
    dict_fields_ids = settings.DICT_USER_FIELDS_IDS
    attachments = {}
    task = task.get("task")
    fields = task.get("fields")
    for field in fields:
        field_id = field.get("id")
        value = dict_fields_ids.get(field_id)
        if value:
            attachments[value] = field.get("value")
    return attachments


async def create_task_by_api(state, telegram_username: str, user_id: int, files: Optional[List] = None) -> bool:
    """
    Создает задачу в Pyrus API на основе данных из состояния
    """
    # Получаем данные из хранилища
    task_data = await extract_task_data(state)

    # Получаем текстовое значение темы
    theme_text = await get_theme_text(task_data["theme_id"])

    user_data = {}

    if task_data["user_task_id"]:
        task = await PyrusService.get_task_by_id(task_data["user_task_id"])
        user_data = await extract_user_info(task)


    # Формируем основной JSON для запроса
    json_data = build_task_json(
        theme_text=theme_text,
        text_problem=task_data["text_problem"],
        contractor_id=task_data["contractor_id"],
        user_task_id=task_data["user_task_id"],
        pc_name=task_data["pc_name"],
        telephone_number=task_data["telephone_number"],
        fullname=task_data["fullname"],
        user_id=user_id,
        telegram_username=telegram_username,
        files=files,
        user_data=user_data
    )

    # Отправляем запрос в Pyrus
    result = await PyrusService.create_task(json_data)
    task_id = result.get("task").get("id")
    return task_id

async def extract_task_data(state) -> Dict[str, Union[str, int]]:
    """
    Извлекает необходимые данные из состояния
    """
    data = await state.get_data()
    return {
        "user_task_id": data.get("user_task_id"),
        "telephone_number": data.get("telephone_number"),
        "pc_name": data.get("pc_name"),
        "theme_id": data.get("theme_id"),
        "text_problem": data.get("text_problem"),
        "contractor_id": data.get("contractor_id"),
        'fullname': data.get("fullname"),
    }


async def get_theme_text(theme_id: int) -> str:
    """
    Получает текстовое значение темы по её ID
    """
    items = await PyrusService.get_items()
    return get_value_by_item_id(theme_id, items)


def build_task_json(
        theme_text: str,
        text_problem: str,
        contractor_id: int,
        user_task_id: Optional[int] = None,
        pc_name: Optional[str] = None,
        telephone_number: Optional[str] = None,
        fullname: Optional[str] = None,
        user_id: Optional[int] = None,
        telegram_username: Optional[str] = None,
        files: Optional[List] = None,
        user_data: Optional[Dict] = None
) -> Dict:
    """
    Строит JSON для создания задачи в Pyrus
    """
    now_utc = datetime.now(timezone.utc)
    now_utc = now_utc.replace(microsecond=(now_utc.microsecond // 1000) * 1000)
    iso_format_z = now_utc.isoformat().replace('+00:00', 'Z')

    if not user_task_id:
        text_problem +=f'\n\n⚠️ ФИО отправителя: {fullname}'

    # Базовые поля, которые всегда присутствуют
    fields = [
        {"code": "Subject", "value": theme_text},
        {"code": "Message", "value": text_problem},
        {"id": 40, "value": {"task_id": int(contractor_id)}},
        {"id": 71, "value": {"choice_id": 1}},
        {"id": 12, "value": {"choice_id": 3}},
        {"id": 68, "value": iso_format_z},


    ]

    # Добавляем файлы, если они есть
    if files:
        fields.append({"id": 35, "value": files})

    # Добавляем поля в зависимости от наличия user_task_id
    if user_task_id:
        fields.append({
            "id": 39,
            "value": {"task_id": user_task_id},
        }
        )
        fields.append({
            "id": 6,
            "value": user_data.get("first_phone"),
        }
        )
        fields.append({
            "id": 58,
            "value": user_data.get("second_phone"),
        }
        )
        fields.append({
            "id": 42,
            "value": user_data.get("telegram"),
        }
        )
        fields.append({
            "id": 43,
            "value": user_data.get("whatsapp"),
        }
        )
        fields.append({
            "id": 5,
            "value": user_data.get("email"),
        }
        )
        fields.append({
            "id": 44,
            "value": user_data.get("name_pc"),
        }
        )
        fields.append({
            "id": 45,
            "value": user_data.get("note"),
        }
        )
        fields.append({
            "id": 72,
            "value": user_id,
        }
        )
    else:
        if pc_name:
            fields.append({"id": 44, "value": pc_name})
        if telephone_number:
            fields.append({"code": "telephone", "value": telephone_number})
        if user_id and telegram_username:
            fields.append({"id": 73, "value": f"{user_id},{telegram_username}"})

    return {
        "form_id": 2303165,
        "fields": fields
    }

