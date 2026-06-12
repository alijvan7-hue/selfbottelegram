from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.core.config import config
from app.core.database import AsyncSessionFactory
from app.services.log_service import LogService
from app.services.meme_service import MemeService
from app.services.user_service import UserService
from app.utils.date_helper import to_jalali
from app.utils.text_helper import fa_number

router = Router(name="user_management")
logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


@router.message(F.text == "👥 کاربران")
async def users_panel(message: Message, is_admin: bool, **kwargs) -> None:
    if not is_admin:
        return
    async with AsyncSessionFactory() as session:
        svc = UserService(session)
        count = await svc.count_all()

    await message.answer(
        f"👥 <b>مدیریت کاربران</b>\n\n"
        f"تعداد کل: <b>{fa_number(count)}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "دستورات:\n\n"
        "🔍 اطلاعات کاربر:\n<code>/user 123456789</code>\n\n"
        "🚫 بن کاربر:\n"
        "<code>/ban 123456789 7d</code>\n"
        "<code>/ban 123456789 30d</code>\n"
        "<code>/ban 123456789 permanent</code>\n\n"
        "✅ رفع بن:\n<code>/unban 123456789</code>\n\n"
        "🪙 افزایش توکن:\n<code>/addtoken 123456789 10</code>\n\n"
        "🪙 کاهش توکن:\n<code>/removetoken 123456789 5</code>\n\n"
        "📊 تنظیم محدودیت:\n"
        "<code>/setlimit 123456789 5</code>\n"
        "<code>/setlimit 123456789 unlimited</code>"
    )


@router.message(Command("user"))
async def cmd_user_info(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer(
            "⚠️ <b>فرمت صحیح:</b>\n"
            "<code>/user 123456789</code>\n\n"
            "<i>آیدی عددی تلگرام کاربر را وارد کنید</i>"
        )
        return

    if not parts[1].lstrip("-").isdigit():
        await message.answer("❌ آیدی باید عدد باشد.\n<code>/user 123456789</code>")
        return

    target_id = int(parts[1])
    async with AsyncSessionFactory() as session:
        svc = UserService(session)
        meme_svc = MemeService(session)
        user = await svc.get_by_telegram_id(target_id)
        if not user:
            await message.answer(f"❌ کاربر <code>{target_id}</code> یافت نشد.")
            return

        stats = await meme_svc.get_user_stats(user.id)
        level = await svc.get_level(user)

    ban_status = "✅ آزاد"
    if user.is_banned:
        ban_status = "🚫 دائمی" if user.ban_type == "permanent" else f"🚫 تا {to_jalali(user.ban_until)}"

    await message.answer(
        f"👤 <b>اطلاعات کاربر</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"نام: <b>{user.full_name}</b>\n"
        f"یوزر: @{user.username or '—'}\n"
        f"آیدی: <code>{user.telegram_id}</code>\n\n"
        f"🪙 توکن: <b>{fa_number(user.tokens)}</b>\n"
        f"📅 ماهانه: <b>{fa_number(user.monthly_tokens)}</b>\n"
        f"🏅 سطح: <b>{level.name if level else '—'}</b>\n\n"
        f"🎭 میم کل: {fa_number(stats['total'])}\n"
        f"✅ تایید: {fa_number(stats['approved'])}\n"
        f"❌ رد: {fa_number(stats['rejected'])}\n\n"
        f"🔒 وضعیت: {ban_status}\n"
        f"📊 محدودیت: {'بی‌نهایت' if user.no_limit else (user.custom_daily_limit or 'پیش‌فرض')}\n"
        f"📅 عضویت: {to_jalali(user.joined_at)}"
    )


@router.message(Command("ban"))
async def cmd_ban(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.answer(
            "⚠️ <b>فرمت صحیح:</b>\n"
            "<code>/ban 123456789 7d</code> — ۷ روز\n"
            "<code>/ban 123456789 30d</code> — ۳۰ روز\n"
            "<code>/ban 123456789 permanent</code> — دائمی"
        )
        return

    if not parts[1].lstrip("-").isdigit():
        await message.answer("❌ آیدی باید عدد باشد.\n<code>/ban 123456789 7d</code>")
        return

    if parts[2] not in ("7d", "30d", "permanent"):
        await message.answer(
            "❌ نوع بن اشتباه است.\n\n"
            "مقادیر مجاز:\n"
            "• <code>7d</code> — ۷ روز\n"
            "• <code>30d</code> — ۳۰ روز\n"
            "• <code>permanent</code> — دائمی"
        )
        return

    target_id = int(parts[1])
    ban_type = parts[2]
    now = datetime.now(timezone.utc)
    ban_until = None
    if ban_type == "7d":
        ban_until = now + timedelta(days=7)
    elif ban_type == "30d":
        ban_until = now + timedelta(days=30)

    async with AsyncSessionFactory() as session:
        svc = UserService(session)
        log_svc = LogService(session)
        user = await svc.get_by_telegram_id(target_id)
        if not user:
            await message.answer(f"❌ کاربر <code>{target_id}</code> یافت نشد.")
            return

        await svc.ban_user(user, ban_type, ban_until)
        await log_svc.user_banned(target_id, ban_type, message.from_user.id)
        await session.commit()

    duration_fa = {"7d": "۷ روز", "30d": "۳۰ روز", "permanent": "دائمی"}
    await message.answer(
        f"🚫 کاربر <code>{target_id}</code> بن شد.\n"
        f"مدت: <b>{duration_fa[ban_type]}</b>"
    )


@router.message(Command("unban"))
async def cmd_unban(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer(
            "⚠️ <b>فرمت صحیح:</b>\n"
            "<code>/unban 123456789</code>"
        )
        return

    if not parts[1].lstrip("-").isdigit():
        await message.answer("❌ آیدی باید عدد باشد.\n<code>/unban 123456789</code>")
        return

    target_id = int(parts[1])
    async with AsyncSessionFactory() as session:
        svc = UserService(session)
        user = await svc.get_by_telegram_id(target_id)
        if not user:
            await message.answer(f"❌ کاربر <code>{target_id}</code> یافت نشد.")
            return
        await svc.unban_user(user)
        await session.commit()

    await message.answer(f"✅ بن کاربر <code>{target_id}</code> برداشته شد.")


@router.message(Command("addtoken"))
async def cmd_add_token(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.answer(
            "⚠️ <b>فرمت صحیح:</b>\n"
            "<code>/addtoken 123456789 10</code>"
        )
        return

    if not parts[1].lstrip("-").isdigit() or not parts[2].isdigit():
        await message.answer(
            "❌ فرمت اشتباه.\n"
            "<code>/addtoken 123456789 10</code>"
        )
        return

    target_id, amount = int(parts[1]), int(parts[2])
    async with AsyncSessionFactory() as session:
        svc = UserService(session)
        user = await svc.get_by_telegram_id(target_id)
        if not user:
            await message.answer(f"❌ کاربر <code>{target_id}</code> یافت نشد.")
            return
        await svc.add_tokens(user, amount)
        await session.commit()

    await message.answer(
        f"✅ {fa_number(amount)} توکن به کاربر <code>{target_id}</code> اضافه شد.\n"
        f"توکن فعلی: {fa_number(user.tokens)}"
    )


@router.message(Command("removetoken"))
async def cmd_remove_token(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.answer(
            "⚠️ <b>فرمت صحیح:</b>\n"
            "<code>/removetoken 123456789 5</code>"
        )
        return

    if not parts[1].lstrip("-").isdigit() or not parts[2].isdigit():
        await message.answer(
            "❌ فرمت اشتباه.\n"
            "<code>/removetoken 123456789 5</code>"
        )
        return

    target_id, amount = int(parts[1]), int(parts[2])
    async with AsyncSessionFactory() as session:
        svc = UserService(session)
        user = await svc.get_by_telegram_id(target_id)
        if not user:
            await message.answer(f"❌ کاربر <code>{target_id}</code> یافت نشد.")
            return
        await svc.remove_tokens(user, amount)
        await session.commit()

    await message.answer(
        f"✅ {fa_number(amount)} توکن از کاربر <code>{target_id}</code> کم شد.\n"
        f"توکن فعلی: {fa_number(user.tokens)}"
    )


@router.message(Command("setlimit"))
async def cmd_set_limit(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.answer(
            "⚠️ <b>فرمت صحیح:</b>\n"
            "<code>/setlimit 123456789 5</code> — ۵ میم در روز\n"
            "<code>/setlimit 123456789 unlimited</code> — بی‌نهایت"
        )
        return

    if not parts[1].lstrip("-").isdigit():
        await message.answer("❌ آیدی باید عدد باشد.")
        return

    target_id = int(parts[1])
    limit_str = parts[2]

    async with AsyncSessionFactory() as session:
        svc = UserService(session)
        user = await svc.get_by_telegram_id(target_id)
        if not user:
            await message.answer(f"❌ کاربر <code>{target_id}</code> یافت نشد.")
            return

        if limit_str.lower() == "unlimited":
            user.no_limit = True
            user.custom_daily_limit = None
            msg = f"✅ محدودیت کاربر <code>{target_id}</code> حذف شد (بی‌نهایت)."
        elif limit_str.isdigit():
            user.no_limit = False
            user.custom_daily_limit = int(limit_str)
            msg = f"✅ محدودیت کاربر <code>{target_id}</code> به <b>{limit_str}</b> میم در روز تنظیم شد."
        else:
            await message.answer(
                "❌ مقدار نامعتبر.\n\n"
                "مقادیر مجاز:\n"
                "• عدد (مثل <code>5</code>)\n"
                "• <code>unlimited</code> برای بی‌نهایت"
            )
            return

        await session.commit()

    await message.answer(msg)