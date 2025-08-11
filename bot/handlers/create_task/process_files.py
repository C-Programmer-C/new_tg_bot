import logging
import uuid
from aiogram import types
from bot.clients.redis_client import RedisClient
from bot.services.file_service import FileService
from bot.states.create_task import CreateTask
from . import create_task_router
from aiogram import F
from bot.keyboards.main_menu import MainMenuKeyboards
from bot.texts.task_actions import TaskActionsMessages
from aiogram.fsm.context import FSMContext
from .post_task_info import handle_post_comment
from aiogram.types import ReplyKeyboardRemove

from ..main_menu.main_menu import send_main_menu
from ...texts.create_task import CreateTaskMessages
from ...utils.can_reset_files import can_reset_files
from ...utils.check_cooldown import check_cooldown
from ...utils.delete_keys_from_redis import delete_keys_by_pattern_async

logger = logging.getLogger(__name__)

@create_task_router.message(CreateTask.add_files, F.text == "Вернуться в главное меню")
async def back_to_main_menu(message: types.Message, state: FSMContext ):
    redis = await RedisClient.get_instance()
    if not await can_reset_files(redis, message.from_user.id, message):
        return
    await message.answer(TaskActionsMessages.RETURN_TO_MAIN_MENU, reply_markup=ReplyKeyboardRemove())
    pattern = f"create_task_file_{message.from_user.id}_*"
    await delete_keys_by_pattern_async(redis, pattern)
    processing_key = f"media_processing:{message.from_user.id}"
    await redis.delete(processing_key)
    await state.clear()
    await send_main_menu(message, state)


@create_task_router.message(CreateTask.add_files, F.text == "Сбросить файлы")
async def handle_reset_files(
        message: types.Message,
) -> None:
    """Обработчик сброса прикрепленных файлов"""
    try:
        redis = await RedisClient.get_instance()

        user_id = message.from_user.id
        cooldown_key = f"reset_files_cooldown:{user_id}"

        # Проверяем кулдаун
        if not await check_cooldown(redis, cooldown_key):
            await message.answer(
                TaskActionsMessages.COOLDOWN_MESSAGE,
            )
            return

        if not await can_reset_files(redis, message.from_user.id, message):
            return
        pattern = f"create_task_file_{message.from_user.id}_*"
        is_files_found = await delete_keys_by_pattern_async(redis, pattern)
        if is_files_found:
            await message.answer(TaskActionsMessages.CORRECT_CLEAR_FILES_MESSAGE)
        else:
            await message.answer(TaskActionsMessages.NOT_FOUND_CLEAR_FILES_MESSAGE)
    except Exception as e:
        logger.exception(f"Failed to reset files: {e}")
        await message.answer(
            TaskActionsMessages.SERVER_ERROR_MESSAGE,
            reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
        )

@create_task_router.message(CreateTask.add_files)
async def handle_single_file(message: types.Message, state: FSMContext):
    """Обработка файлов"""
    if message.text and message.text == "Отправить":
        await handle_post_comment(message, state)
        return
    if message.text:
        return
    redis = await RedisClient.get_instance()
    processing_key = f"media_processing:{message.from_user.id}"
    lock_key = f"final_notify_lock:{message.from_user.id}"
    file_key = f"create_task_file_{message.from_user.id}_{uuid.uuid4().hex}"
    try:
        current_count = await redis.incr(processing_key)
        if current_count == 1:
            await redis.expire(processing_key, 3600)
        result = await FileService.process_single_file(message, file_key, redis)
        if result:
            await message.reply(result)

    except Exception as e:
        user_id = message.from_user.id
        logger.exception(f"Ошибка обработки файла от пользователя {user_id}: {e}")
        await message.answer("Произошла ошибка при обработке файла. Попробуйте позже.")
    finally:
        try:
            current_count = await redis.decr(processing_key)
            async with redis.lock(lock_key, timeout=5):
                if current_count <= 0:
                    await redis.delete(processing_key)
                    await message.answer(CreateTaskMessages.PROCESS_CORRECT_FILES_DONE_MESSAGE)
        except Exception as e:
            user_id = message.from_user.id
            logger.exception(f"Ошибка при уменьшении счетчика {user_id}: {e}")