import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.types import BotCommand

from bot.clients.bot_client import BotClient
from bot.clients.redis_client import RedisClient
from config import settings
from bot.handlers.main_menu import start_router
from bot.scheduler import periodic_task_fetcher
from bot.handlers.task_actions import task_actions_router
from bot.handlers.create_task import create_task_router
from bot.handlers.closed_tasks import closed_tasks_router

logger = logging.getLogger(__name__)
_periodic_task: asyncio.Task | None = None
disp = None

async def on_startup():
    print("▶️ on_startup fired")
    # Инициализация Redis и FSM storage
    redis = await RedisClient.get_instance()
    await redis.flushall()
    disp.fsm_storage = RedisStorage(
        redis=redis,
        key_builder=DefaultKeyBuilder(with_destiny=True),
    )

    # Установка команд бота через dp.bot
    bot: Bot = BotClient.get_instance()
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="cancel", description="Отмена"),
    ])

    # Запуск фоновой задачи
    global _periodic_task
    _periodic_task = asyncio.create_task(periodic_task_fetcher())
    logger.info("🚀 periodic_task_fetcher запущен")

async def on_shutdown():
    print("▶️ on_shutdown fired")
    global _periodic_task
    if _periodic_task:
        _periodic_task.cancel()
        try:
            await _periodic_task
        except asyncio.CancelledError:
            pass

    # Закрываем клиентов
    await BotClient.close()
    await RedisClient.close()
    logger.info("⛔ Бот остановлен")

async def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format="%(asctime)s - [%(levelname)s] - %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s",
        handlers=[
            logging.FileHandler("bot.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    print("▶️ Entering main()")

    # Инициализация Bot и Dispatcher
    bot = BotClient.get_instance()
    global disp
    dp = Dispatcher()
    disp = dp
    # Регистрируем роутеры
    for router in (
        start_router,
        task_actions_router,
        create_task_router,
        closed_tasks_router,
    ):
        dp.include_router(router)

    # Регистрируем lifecycle-хуки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("🚀 Запуск polling")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.critical(f"Неожиданная ошибка: {e}")
        raise
