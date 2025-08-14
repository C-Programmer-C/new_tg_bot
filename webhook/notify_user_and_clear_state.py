# python 3.10+
from aiogram import Bot
from aiogram.fsm.storage.base import StorageKey, DefaultKeyBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message

from bot.clients.redis_client import RedisClient
from bot.main import disp
from bot.clients.bot_client import BotClient
import logging

async def notify_user_and_clear_state(user_id: int, new_message_text: str,
                                      forward_from_chat_id: int | None = None,
                                      forward_message_id: int | None = None):
    """
    - user_id: telegram user id (в приватном чате chat_id == user_id)
    - new_message_text: текст, который нужно отправить пользователю
    - если нужно переслать конкретное сообщение, укажи forward_from_chat_id и forward_message_id
    """
    try:

        print("Я запускаюсь!")
        bot_client = BotClient.get_instance()
        bot: Bot = bot_client
        redis = await RedisClient.get_instance()
        storage = RedisStorage(redis=redis, key_builder=DefaultKeyBuilder(with_destiny=True))
        me = await bot.get_me()
        bot_id = me.id

        key = StorageKey(bot_id=bot_id, chat_id=user_id, user_id=user_id)

        current_state = await storage.get_state(key=key)  # None или str



        if current_state:
            fsm = FSMContext(storage=storage, key=key)
            await fsm.clear()

            apologize_text = (
                "🙏 Извините — у вас был незавершённый диалог с ботом, "
                "мы автоматически его закрыли 🗑 и получили новое сообщение ✉️."
            )
            await bot.send_message(chat_id=user_id, text=apologize_text)


        await bot.send_message(chat_id=user_id, text=new_message_text)
        logging.info(f"Сообщение было успешно отправлено пользователю с id: {user_id}")

    except Exception as e:
        logging.exception(f"Ошибка при отправке сообщения пользователю с id: {user_id}:\n{e}")