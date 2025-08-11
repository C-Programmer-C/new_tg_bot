from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.config import settings

def build_closed_tasks_keyboard(tasks: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for idx, task in enumerate(tasks):
        task_id = task['id']
        title = next(
            (f["value"] for f in task.get("fields", []) if f.get("id") == 1),
            "Без названия"
        )
        emoji = settings.NUMBERS_EMOJI[idx] if idx < len(settings.NUMBERS_EMOJI) else "📝"
        builder.button(
            text=f"{emoji} {title} (#{task_id})",
            callback_data=f"closed_task_{task['id']}"
        )
    builder.button(text="↩️ Вернуться в главное меню", callback_data="closed_tasks_back_to_menu")
    builder.adjust(2)
    return builder.as_markup()