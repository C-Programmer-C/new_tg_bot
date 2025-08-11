from aiogram import types
from bot.config import settings
import asyncio
import io
import logging
from typing import List, Dict, Optional
from aiogram import Bot

from bot.services.pyrus_api_service import PyrusService

logger = logging.getLogger(__name__)


class FileService:
    MAX_FILE_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024  # Конвертируем МБ в байты

    @staticmethod
    async def process_single_file(
        message: types.Message,
        file_key,
        redis
    ) -> str | None:
        """Обработка файлов с правильной проверкой размера"""
        try:
            file_id, filename, file_size = FileService.identify_file_data(message)
            if not file_id:
                return "⚠️ Неподдерживаемый тип файла"

            if file_size > settings.MAX_FILE_SIZE:
                return "⚠️ Файл слишком большой! Максимум 20МБ"

            await redis.hset(
                file_key,
                mapping={
                    "file_id": file_id,
                    "filename": filename,
                }
            )

            return

        except Exception as e:
            logger.error(f"File processing error: {e}")
            return "⚠️ Ошибка обработки файла"

    @staticmethod
    def identify_file_data(message: types.Message) -> tuple:
        """Определение file_id и имени файла"""
        if message.photo:
            file = message.photo[-1]
            return file.file_id, f"photo_{file.file_id}.jpg", file.file_size
        elif message.document:
            return message.document.file_id, message.document.file_name, message.document.file_size
        elif message.audio:
            return message.audio.file_id, f"audio_{message.audio.file_id}.mp3", message.audio.file_size
        elif message.voice:
            return message.voice.file_id, f"voice_{message.voice.file_id}.ogg", message.voice.file_size
        elif message.video:
            return message.video.file_id, f"video_{message.video.file_id}.mp4", message.video.file_size
        elif message.sticker:  # Добавляем обработку стикеров
            sticker = message.sticker
            # Определяем формат на основе типа стикера
            if sticker.is_animated:  # Анимированные стикеры (TGS)
                ext = "tgs"
            elif sticker.is_video:  # Видео-стикеры (WEBM)
                ext = "webm"
            else:  # Статичные стикеры (WEBP)
                ext = "webp"
            return sticker.file_id, f"sticker_{sticker.file_id}.{ext}", sticker.file_size
        return None, None, None


    @staticmethod
    async def prepare_files(files: List[Dict], bot: Bot) -> Optional[List[str]]:
        """Подготавливает файлы для отправки в Pyrus"""
        if not files:
            return None
        tasks = []
        for file in files:
            tasks.append(FileService._process_file(file["file_id"], file["filename"], bot))

        try:
            results = await asyncio.gather(*tasks)
            return [file_id for file_id in results if file_id]
        except Exception as e:
            logger.error(f"File preparation error: {e}")
            return None

    @staticmethod
    async def _process_file(file_id: str, filename: str, bot: Bot) -> Optional[str]:
        """Обрабатывает один файл"""
        try:
            file = await bot.get_file(file_id)
            file_bytes = io.BytesIO()
            await bot.download_file(file.file_path, destination=file_bytes)
            file_bytes.seek(0)
            a =  await PyrusService.get_unique_file_id(file_bytes, filename)
            return a
        except Exception as e:
            logger.error(f"Failed to process file {filename}: {e}")
            return None