from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from app.core.database import AsyncSessionFactory
from app.models.user import User
from app.services.meme_service import MemeService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService
from app.utils.date_helper import to_jalali
from app.utils.text_helper import fa_number

router = Router(name="profile")


@router.message(F.text == "📊 اطلاعات من")
async def profile_handler(message: Message, user: User, **kwargs) -> None:
    async with AsyncSessionFactory() as session:
        user_svc = UserService(session)
        meme_svc = MemeService(session)

        fresh_user = await user_svc.get_by_telegram_id(user.telegram_id)
        if not fresh_user:
            await message.answer("خطا در دریافت اطلاعات.")
            return

        stats = await meme_svc.get_user_stats(fresh_user.id)
        level = await user_svc.get_level(fresh_user)
        level_name = level.name if level else "بدون سطح"

    joined = to_jalali(fresh_user.joined_at)

    text = (
        f"📊 <b>اطلاعات من</b>\n\n"
        f"👤 نام: <b>{fresh_user.full_name}</b>\n"
        f"🆔 آیدی: <code>{fresh_user.telegram_id}</code>\n\n"
        f"🎭 میم ثبت‌شده: <b>{fa_number(stats['total'])}</b>\n"
        f"✅ تایید شده: <b>{fa_number(stats['approved'])}</b>\n"
        f"❌ رد شده: <b>{fa_number(stats['rejected'])}</b>\n"
        f"⏳ در انتظار: <b>{fa_number(stats['pending'])}</b>\n\n"
        f"🪙 توکن: <b>{fa_number(fresh_user.tokens)}</b>\n"
        f"🏅 سطح: <b>{level_name}</b>\n\n"
        f"📅 تاریخ عضویت: <b>{joined}</b>"
    )
    await message.answer(text)