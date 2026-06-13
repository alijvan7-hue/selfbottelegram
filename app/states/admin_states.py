from aiogram.fsm.state import State, StatesGroup


class AdminAdModStates(StatesGroup):
    waiting_reply_text = State()


class AdminSettingsStates(StatesGroup):
    waiting_value = State()


class AdminUserStates(StatesGroup):
    waiting_action = State()


class AdminQueueStates(StatesGroup):
    waiting_remove_id = State()
    waiting_publish_id = State()
