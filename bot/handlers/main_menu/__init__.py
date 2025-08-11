from aiogram import Router

start_router = Router()

from bot.handlers.main_menu import main_menu

__all__ = ["start_router"]