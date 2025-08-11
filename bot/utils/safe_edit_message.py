async def safe_edit_message(bot, chat_id: int, msg_id: int, text: str, reply_markup=None):
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=text,
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Ошибка при редактировании сообщения: {e}")