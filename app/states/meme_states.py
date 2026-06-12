from aiogram.fsm.state import State, StatesGroup


class MemeSubmitStates(StatesGroup):
    waiting_media = State()