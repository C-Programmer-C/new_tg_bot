import logging
import uuid
from aiogram import types
from bot.clients.redis_client import RedisClient
from bot.services.file_service import FileService
from bot.states.add_comment import AddComment
from bot.utils.can_reset_files import can_reset_files
from bot.utils.check_cooldown import check_cooldown
from bot.utils.delete_keys_from_redis import delete_keys_by_pattern_async
from ... import task_actions_router
from aiogram import F
from bot.keyboards.main_menu import MainMenuKeyboards
from bot.texts.task_actions import TaskActionsMessages

logger = logging.getLogger(__name__)

@task_actions_router.message(AddComment.add_files, F.text == "Сбросить файлы")
async def handle_reset_files(
        message: types.Message,
) -> None:
    """Обработчик сброса прикрепленных файлов"""
    try:
        redis = await RedisClient.get_instance()
        user_id = message.from_user.id
        cooldown_key = f"reset_files_cooldown:{user_id}"

        if not await check_cooldown(redis, cooldown_key):
            await message.answer(
                TaskActionsMessages.COOLDOWN_MESSAGE,
            )
            return
        if not await can_reset_files(redis, message.from_user.id, message):
            return
        pattern = f"file_{message.from_user.id}_*"
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

@task_actions_router.message(AddComment.add_files)
async def handle_single_file(message: types.Message):
    """Обработка файлов"""
    if message.text:
        return
    redis = await RedisClient.get_instance()
    processing_key = f"media_processing:{message.from_user.id}"
    lock_key = f"final_notify_lock:{message.from_user.id}"
    file_key = f"file_{message.from_user.id}_{uuid.uuid4().hex}"
    try:
        await redis.incr(processing_key)
        result = await FileService.process_single_file(message, file_key, redis)
        if result:
            await message.reply(result)

    except Exception as e:
        logger.error(f"File processing error: {e}")
        await message.answer(f"⚠️ Ошибка обработки файла")
    finally:
        async with redis.lock(lock_key, timeout=5):
            current_count = await redis.decr(processing_key)
            if current_count <= 0:
                await redis.delete(processing_key)
                await message.answer(TaskActionsMessages.PROCESS_CORRECT_FILES_DONE_MESSAGE)
