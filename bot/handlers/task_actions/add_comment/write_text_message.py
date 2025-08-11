from aiogram import types, F
from aiogram.fsm.context import FSMContext

from bot.clients.bot_client import BotClient
from bot.states.add_comment import AddComment
from bot.texts.create_task import CreateTaskMessages
from bot.texts.task_actions import TaskActionsMessages
from bot.keyboards.task_actions import TaskActionsKeyboards
from bot.utils.safe_edit_message import safe_edit_message
from bot.utils.validate_text import validate_text
from bot.utils.task_utils import TaskUtils
from .. import task_actions_router
import logging
from bot.keyboards.main_menu import MainMenuKeyboards
from ..task_info import show_task_info_callback

logger = logging.getLogger(__name__)


@task_actions_router.callback_query(AddComment.write_text_message, F.data == 'back_to_task_info')
async def back_to_task_info(callback: types.CallbackQuery, state: FSMContext):
    try:
        await show_task_info_callback(callback, state)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in show_tasks: {e}")
        await callback.message.edit_text(
            TaskActionsMessages.SERVER_ERROR_MESSAGE
        )
        await callback.answer()

@task_actions_router.callback_query(AddComment.show_task_info, F.data.startswith("comment_"))
async def start_comment_process(
        callback: types.CallbackQuery,
        state: FSMContext
):
    """Начало процесса добавления комментария"""
    try:
        task_id = TaskUtils.extract_data_from_callback(callback.data)
        if not task_id:
            logger.error(f"Invalid task ID in callback: {callback.data}")
            await callback.message.edit_text(
                TaskActionsMessages.SERVER_ERROR_MESSAGE,
                reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
            )
            return
        await state.set_state(AddComment.write_text_message)
        msg = await callback.message.edit_text(TaskActionsMessages.WRITE_TEXT_MESSAGE, reply_markup=TaskActionsKeyboards.create_input_text_keyboard(task_id))
        msg_id = msg.message_id
        await state.update_data(msg_id=msg_id)

    except Exception as e:
        logger.exception(f"Error starting comment process: {str(e)}")
        await callback.message.edit_text(
            TaskActionsMessages.SERVER_ERROR_MESSAGE,
            reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
        )


@task_actions_router.message(AddComment.write_text_message)
async def process_comment_text(
        message: types.Message,
        state: FSMContext
):
    """Обработка текста комментария"""
    try:

        comment_text = message.text

        is_correct = await validate_text(text=comment_text,
                                         message=message,
                                         on_empty=TaskActionsMessages.EMPTY_COMMENT_MESSAGE,
                                         on_too_short=TaskActionsMessages.SHORT_COMMENT_MESSAGE,
                                         on_too_long=TaskActionsMessages.LONG_COMMENT_MESSAGE,
                                         min_length=1,
                                         max_length=2000)
        if not is_correct:
            return

        await state.update_data(comment_text=message.text)
        await proceed_to_files(message, state)

    except Exception as e:
        logger.exception(f"Error processing comment text: {str(e)}")
        await message.answer(
            TaskActionsMessages.SERVER_ERROR_MESSAGE,
            reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
        )


@task_actions_router.callback_query(AddComment.write_text_message, F.data == "skip_text")
async def skip_comment_text(
        callback: types.CallbackQuery,
        state: FSMContext
):
    """Пропуск ввода текста комментария"""
    try:
        await state.update_data(comment_text=None)
        await proceed_to_files(callback.message, state)
        await callback.answer()

    except Exception as e:
        logger.exception(f"Error skipping comment text: {str(e)}")
        await callback.message.edit_text(
            TaskActionsMessages.SERVER_ERROR_MESSAGE,
            reply_markup=MainMenuKeyboards.create_back_to_menu_keyboard()
        )
        await callback.answer()

async def proceed_to_files(
        message: types.Message,
        state: FSMContext
):
    """Переход к добавлению файлов"""
    await state.set_state(AddComment.add_files)
    msg_id = (await state.get_data()).get('msg_id')
    bot = BotClient.get_instance()
    await safe_edit_message(bot, message.chat.id, msg_id, TaskActionsMessages.WRITE_TEXT_MESSAGE)
    await message.answer(TaskActionsMessages.ADD_FILES_MESSAGE, reply_markup=TaskActionsKeyboards.create_files_keyboard())