from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

class ItemCallback(CallbackData, prefix="item"):
    item_id: Optional[int] = None

class CreateTaskKeyboards:

    @staticmethod
    async def build_themes_task_keyboard(items):
        """Динамическое клавиатура из справочника Pyrus по API"""
        builder = InlineKeyboardBuilder()
        emoji = "💻"
        for item in items:
            item_id = item.get("item_id")
            value = item.get("values")[0]

            builder.button(
                text=f"{emoji} {value}",
                callback_data=ItemCallback(item_id=item_id).pack()
            )

        builder.button(text="↩️ Вернуться в главное меню", callback_data="themes_to_main_menu")
        builder.adjust(2)
        return builder.as_markup()


    @staticmethod
    def transition_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура с кнопками подтверждения прочтения информации и возврата в меню."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text='✅ Информация прочитана', callback_data='input_fullname'),
                InlineKeyboardButton(text='🔙 Вернуться в меню', callback_data='transition_back_to_menu')
            ],
        ])

    @staticmethod
    def files_keyboard() -> ReplyKeyboardMarkup:
        """Клавиатура управления файлами: отправить, сбросить, вернуться в меню."""
        builder = ReplyKeyboardBuilder()
        builder.add(
            KeyboardButton(text="Отправить"),
            KeyboardButton(text="Сбросить файлы"),
            KeyboardButton(text="Вернуться в главное меню")
        )
        # Распределяем кнопки по рядам (adjust=2 — первые две кнопки в одном ряду)
        builder.adjust(2, 1)
        return builder.as_markup(resize_keyboard=True)


    @staticmethod
    def attach_files_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура для подтверждения добавления файлов."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="add_files"),
                InlineKeyboardButton(text="❌ Нет", callback_data="no_files")
            ]
        ])

    @staticmethod
    def service_quality_keyboard(task_id) -> InlineKeyboardMarkup:
        """Клавиатура для повторного ввода данных или возврата в меню."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐️ Оценить качество обслуживания", callback_data=f"give_mark_{task_id}")],
        ])

    @staticmethod
    def input_data_again_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура для повторного ввода данных или возврата в меню."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Повторить ввод ИНН", callback_data="process_data")],
            [InlineKeyboardButton(text="↩️ Вернуться в главное меню", callback_data="data_again_back_to_main_menu")]
        ])


    @staticmethod
    def service_rating_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура для оценки сервиса (от 1 до 5)"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤩", callback_data="grade_5")],
            [InlineKeyboardButton(text="😀", callback_data="grade_4")],
            [InlineKeyboardButton(text="🙂", callback_data="grade_3")],
            [InlineKeyboardButton(text="😐", callback_data="grade_2")],
            [InlineKeyboardButton(text="😞", callback_data="grade_1")],
            [InlineKeyboardButton(text="🏠 Вернуться в главное меню", callback_data="get_main_menu")]
        ])

    @staticmethod
    def back_to_main_menu() -> InlineKeyboardMarkup:
        """Клавиатура для возвращения в главное меню"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Вернуться в главное меню", callback_data="mark_back_to_main_menu")],
        ])