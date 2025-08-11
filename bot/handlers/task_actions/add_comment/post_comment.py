from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from bot.clients.bot_client import BotClient
from bot.clients.redis_client import RedisClient
from bot.services.file_service import FileService
from bot.services.pyrus_api_service import PyrusService
from bot.states.add_comment import AddComment
from bot.texts.create_task import CreateTaskMessages
from bot.texts.task_actions import TaskActionsMessages
from bot.keyboards.main_menu import MainMenuKeyboards
from bot.utils.can_reset_files import can_reset_files
from bot.utils.delete_keys_from_redis import delete_keys_by_pattern_async
from .. import task_actions_router
import logging
from ...main_menu.main_menu import send_main_menu

logger = logging.getLogger(__name__)

@task_actions_router.message(AddComment.add_files, F.text == "Вернуться в главное меню")
async def back_to_main_menu(message: types.Message, state: FSMContext):
    try:
        redis = await RedisClient.get_instance()
        if not await can_reset_files(redis, message.from_user.id, message):
            return
        pattern = "file_{user_id}_*"
        await delete_keys_by_pattern_async(redis, pattern)
        await state.clear()
        processing_key = f"media_processing:{message.from_user.id}"
        await redis.delete(processing_key)
        await message.answer(TaskActionsMessages.RETURN_TO_MAIN_MENU, reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message, state)
    except Exception as e:
        logger.exception(f"Failed to post comment: {e}")
        await message.answer(
            TaskActionsMessages.SERVER_ERROR_MESSAGE,
            reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
        )
@task_actions_router.message(F.text == "Отправить комментарий")
async def handle_post_comment(message: types.Message, state: FSMContext):
    """Обработчик отправки комментария"""
    try:
        redis = await RedisClient.get_instance()
        processing_key = f"media_processing:{message.from_user.id}"
        user_id = message.from_user.id
        if await redis.exists(processing_key):
            count = int(await redis.get(processing_key))
            if count > 0:
                await message.answer(CreateTaskMessages.MESSAGE_WAIT_PROCESS_FILES)
                return
        keys = await redis.keys(f"file_{user_id}_*")
        data = await state.get_data()
        text = data.get("comment_text")
        if not keys and not text:
            await message.answer(CreateTaskMessages.MESSAGE_NOT_FILES_FOR_CREATE_TASK)
            return
        await message.answer(TaskActionsMessages.WAIT_CREATE_COMMENT_MESSAGE, reply_markup=ReplyKeyboardRemove())
        data = await state.get_data()
        text = data.get("comment_text")
        task_id = data.get("task_id")
        bot = BotClient.get_instance()
        files = []
        for key in keys:
            if not await redis.exists(key):
                continue
            file_data = await redis.hgetall(key)
            files.append({
                "file_id": file_data.get("file_id"),
                "filename": file_data.get("filename")
            })
        # Подготовка файлов
        file_ids = await FileService.prepare_files(
            files=files,
            bot=bot,
        ) if files else None

        task = await PyrusService.get_task_by_id(task_id)
        if not task:
            return
        task_data =  task.get("task")
        is_closed =  task_data.get("close_date")
        if is_closed:
            await PyrusService.open_task(task_id)
        # Отправка комментария
        success = await PyrusService.post_comment_files(
            task_id=task_id,
            text=text,
            files=file_ids
        )

        if success:
            await message.answer(
                TaskActionsMessages.POST_MESSAGE_TEXT,
                reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
            )
            pattern = "file_{user_id}_*"
            await delete_keys_by_pattern_async(redis, pattern)


        else:
            await message.answer(
                TaskActionsMessages.SERVER_ERROR_MESSAGE,
                reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
            )

        await state.clear()
        await redis.delete(processing_key)
        pattern = f"file_{message.from_user.id}_*"

        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)

    except Exception as e:
        logger.exception(f"Failed to post comment: {e}")
        await message.answer(
            TaskActionsMessages.SERVER_ERROR_MESSAGE,
            reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
        )