from aiogram.fsm.state import State, StatesGroup

class ClosedTasks(StatesGroup):
    show_closed_tasks = State()
    show_closed_task_info = State()
    open_task = State()