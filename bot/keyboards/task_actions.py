from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from bot.config import settings
from typing import List, Dict


class TaskActionsKeyboards:

    @staticmethod
    def create_input_text_keyboard(task_id):
        """Клавиатура для действий с текстом"""
        inline_keyboard = [
            [InlineKeyboardButton(text="➡️ Пропустить", callback_data="skip_text")],
            [InlineKeyboardButton(text="↩️ Назад к обращению", callback_data=f"back_to_task_info")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    @staticmethod
    def create_files_keyboard() -> ReplyKeyboardMarkup:
        keyboard = [
            [KeyboardButton(text="Отправить комментарий"), KeyboardButton(text="Сбросить файлы")],
            [KeyboardButton(text="Вернуться в главное меню")],
        ]
        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    @staticmethod
    def create_actions_keyboard(task_id: int) -> InlineKeyboardMarkup:
        """Клавиатура действий с задачей"""
        buttons = [
            [
                InlineKeyboardButton(
                    text='💬 Добавить комментарий',
                    callback_data=f'comment_{task_id}'
                ),
            ],
            [
                InlineKeyboardButton(
                    text='❌ Отменить обращение',
                    callback_data=f'cancel_{task_id}'
                ),
            ],
            [
                InlineKeyboardButton(
                    text='🔙 Назад к задачам',
                    callback_data='show_tasks'
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def create_task_keyboard(tasks: List[Dict]) -> InlineKeyboardMarkup:
        """Генерация клавиатуры для списка задач."""
        buttons = []
        for idx, task in enumerate(tasks):
            task_id = task.get("id")
            title = next(
                (f["value"] for f in task.get("fields", []) if f.get("id") == 1),
                "Без названия"
            )

            emoji = settings.NUMBERS_EMOJI[idx] if idx < len(settings.NUMBERS_EMOJI) else "📝"
            buttons.append(
                InlineKeyboardButton(
                    text=f"{emoji} {title} (#{task_id})",
                    callback_data=f"task_{task_id}"
                )
            )

        # Оптимальное распределение кнопок (2 в ряд)
        keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
        keyboard.append([
            InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_main_menu")
        ])

        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def create_empty_tasks_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура для случая когда задач нет."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='🆕 Создать обращение', callback_data='process_data')],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main_menu")]
        ])

    @staticmethod
    def get_text_edit_keyboard(task_id: int) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"task_{task_id}"
                )
            ]
        ])