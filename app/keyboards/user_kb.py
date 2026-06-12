from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="🎭 ارسال میم"), KeyboardButton(text="📢 تبلیغات")],
        [KeyboardButton(text="📊 اطلاعات من"), KeyboardButton(text="🏆 لیدربرد")],
        [KeyboardButton(text="📞 پشتیبانی")],
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="🔐 پنل ادمین")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def ads_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 تبلیغات بنری")],
            [KeyboardButton(text="📢 تبلیغات تک خطی")],
            [KeyboardButton(text="🔙 بازگشت")],
        ],
        resize_keyboard=True,
    )


def leaderboard_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏆 لیدربرد کلی"), KeyboardButton(text="🏆 لیدربرد ماهانه")],
            [KeyboardButton(text="🔙 بازگشت")],
        ],
        resize_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ انصراف")]],
        resize_keyboard=True,
    )


def skip_cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭ رد کردن"), KeyboardButton(text="❌ انصراف")]
        ],
        resize_keyboard=True,
    )


def yes_no_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ بله"), KeyboardButton(text="❌ خیر")]
        ],
        resize_keyboard=True,
    )


def duration_banner_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏱ ۱۲ ساعته"), KeyboardButton(text="⏱ ۲۴ ساعته")],
            [KeyboardButton(text="⏱ ۷۲ ساعته")],
            [KeyboardButton(text="❌ انصراف")],
        ],
        resize_keyboard=True,
    )


def duration_oneliner_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="7 روز"), KeyboardButton(text="14 روز")],
            [KeyboardButton(text="21 روز"), KeyboardButton(text="30 روز")],
            [KeyboardButton(text="❌ انصراف")],
        ],
        resize_keyboard=True,
    )
