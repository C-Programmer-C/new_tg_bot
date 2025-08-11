from aiogram import Router

task_actions_router = Router()

from bot.handlers.task_actions import show_tasks, task_info, close_task
from bot.handlers.task_actions.add_comment import write_text_message, post_comment
from bot.handlers.task_actions.add_comment.accept_files import process_files

__all__ = ["task_actions_router"]