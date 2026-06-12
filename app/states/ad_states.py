from aiogram.fsm.state import State, StatesGroup


class BannerAdStates(StatesGroup):
    waiting_text = State()
    waiting_image = State()
    waiting_extra = State()
    waiting_duration = State()
    waiting_reply_choice = State()
    waiting_reply_text = State()      # ← جدید: متن ریپلای از کاربر
    waiting_pin_choice = State()
    waiting_discount = State()
    waiting_receipt = State()


class OnelineAdStates(StatesGroup):
    waiting_text = State()
    waiting_link = State()
    waiting_duration = State()
    confirm = State()
    waiting_discount = State()
    waiting_receipt = State()
