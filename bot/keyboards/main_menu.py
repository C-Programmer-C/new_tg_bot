from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class MainMenuKeyboards:

    @staticmethod
    def create_main_menu_keyboard():
        """Клавиатура для главного меню"""
        inline_keyboard = [
            [
                InlineKeyboardButton(text='📝 Создать обращение', callback_data='process_data')
            ],
            [
                InlineKeyboardButton(text='💬 Комментарий / ❌ Отмена', callback_data='tasks')
            ],
            [
                InlineKeyboardButton(text='📁 Закрытые задачи', callback_data='closed_tasks')
            ],
            [
                InlineKeyboardButton(text='📞 Контакты', callback_data='contacts_info'),
                InlineKeyboardButton(text='ℹ️ О нас', callback_data='company_info')
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    @staticmethod
    def create_back_to_menu_keyboard():
        """Клавиатура для возвращения в главного меню"""
        inline_keyboard = [
            [
                InlineKeyboardButton(text='🔙 Вернуться в меню', callback_data='closed_tasks_back_to_menu')
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

