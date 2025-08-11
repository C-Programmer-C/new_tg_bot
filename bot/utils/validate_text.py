from typing import Optional

from aiogram.types import Message

async def validate_text(
    text: Optional[str],
    message: Message,
    on_empty: str,
    on_too_short: str,
    on_too_long: str,
    min_length: int,
    max_length: int = 2000,
    ) -> bool:
    """
    Валидирует текст и отправляет сообщение об ошибке при необходимости
    :param text: Проверяемый текст
    :param message: Объект Message для отправки сообщения
    :param min_length: Минимальная допустимая длина
    :param max_length: Максимальная допустимая длина (по умолчанию 2000)
    :param on_empty: Сообщение для пустого текста
    :param on_too_short: Сообщение для слишком короткого текста
    :param on_too_long: Сообщение для слишком длинного текста
    :return: True если текст валиден, иначе False
    """
    if not text:
        await message.answer(on_empty)
        return False

    text_length = len(text)

    if text_length < min_length:
        await message.answer(on_too_short)
        return False

    if text_length > max_length:
        await message.answer(on_too_long)
        return False

    return True