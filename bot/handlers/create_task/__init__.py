from aiogram import Router

create_task_router = Router()

from bot.handlers.create_task import post_task_info, process_files, process_task_info, registation_user, validate_identity_number, give_mark

__all__ = ["create_task_router"]