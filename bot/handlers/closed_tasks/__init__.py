from aiogram import Router

closed_tasks_router = Router()

from bot.handlers.closed_tasks import open_task, show_tasks, task_info

__all__ = ["closed_tasks_router"]