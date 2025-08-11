from aiogram.fsm.state import State, StatesGroup

class CreateTask(StatesGroup):
    choose_mark = State()
    give_mark = State()
    check_data = State()
    choose_add_files = State()
    input_user_data = State()
    input_identity_number = State()
    input_Fullname = State()
    add_files = State()
    input_problem = State()
    choose_theme = State()
    input_contact = State()
    input_telephone = State()
    input_pc_name = State()
    post_comment = State()