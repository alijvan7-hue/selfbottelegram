from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.core.config import config
from app.core.database import AsyncSessionFactory
from app.keyboards.user_kb import main_menu_kb
from app.services.settings_service import SettingsService

router = Router(name="common")
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    is_admin: bool,
    **kwargs,
) -> None:
    await state.clear()
    name = message.from_user.full_name if message.from_user else "کاربر"
    await message.answer(
        f"👋 سلام <b>{name}</b>!\n\n"
        "به ربات میم و تبلیغات 🪷تریاک خوش آمدید.\n"
        "از منوی زیر گزینه مورد نظر را انتخاب کنید:",
        reply_markup=main_menu_kb(is_admin=is_admin),
    )


@router.message(Command("help"))
async def cmd_help(message: Message, is_admin: bool, **kwargs) -> None:
    async with AsyncSessionFactory() as session:
        settings_svc = SettingsService(session)
        help_text = await settings_svc.get("help_text") or (
            "📖 <b>راهنمای ربات</b>\n\n"
            "🎭 <b>ارسال میم</b> — میم خود را ارسال کنید\n"
            "📢 <b>تبلیغات</b> — ثبت تبلیغ بنری یا تک خطی\n"
            "📊 <b>اطلاعات من</b> — مشاهده آمار و توکن‌ها\n"
            "🏆 <b>لیدربرد</b> — رتبه‌بندی کاربران\n"
            "📞 <b>پشتیبانی</b> — ارتباط با پشتیبانی"
        )
    await message.answer(help_text, reply_markup=main_menu_kb(is_admin=is_admin))


@router.message(F.text == "🔙 بازگشت")
async def back_to_main(
    message: Message,
    state: FSMContext,
    is_admin: bool,
    **kwargs,
) -> None:
    await state.clear()
    await message.answer("منوی اصلی:", reply_markup=main_menu_kb(is_admin=is_admin))


@router.message(F.text == "❌ انصراف")
async def cancel_action(
    message: Message,
    state: FSMContext,
    is_admin: bool,
    **kwargs,
) -> None:
    await state.clear()
    await message.answer("عملیات لغو شد.", reply_markup=main_menu_kb(is_admin=is_admin))
