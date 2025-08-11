from aiogram.fsm.state import State, StatesGroup

class AddComment(StatesGroup):
    close_task = State()
    show_task_info = State()
    choose_task = State()
    write_text_message = State()
    add_files = State()