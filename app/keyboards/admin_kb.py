from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def admin_main_kb() -> ReplyKeyboardMarkup:
    """پنل ادمین به صورت دکمه‌های پایین صفحه مثل منوی اصلی"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 صف انتشار"),
                KeyboardButton(text="📢 تبلیغات پندینگ"),
            ],
            [
                KeyboardButton(text="💰 درآمد"),
                KeyboardButton(text="📈 آمار"),
            ],
            [
                KeyboardButton(text="👥 کاربران"),
                KeyboardButton(text="⚙️ تنظیمات"),
            ],
            [
                KeyboardButton(text="🏷 تخفیف‌ها"),
                KeyboardButton(text="🎯 سطوح"),
            ],
            [
                KeyboardButton(text="📖 راهنمای ادمین"),
                KeyboardButton(text="🔙 منوی اصلی"),
            ],
        ],
        resize_keyboard=True,
    )
