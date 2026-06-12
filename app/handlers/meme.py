from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Animation,
    Message,
    PhotoSize,
    Video,
)

from app.core.config import config
from app.core.database import AsyncSessionFactory
from app.keyboards.inline_kb import meme_review_kb
from app.keyboards.user_kb import cancel_kb, main_menu_kb
from app.models.user import User
from app.services.meme_service import MemeService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService
from app.states.meme_states import MemeSubmitStates
from app.utils.date_helper import now_tehran

router = Router(name="meme")
logger = logging.getLogger(__name__)

_ALLOWED_TYPES = ("photo", "video", "animation")


# ── Entry point ────────────────────────────────────────────────────────────────
@router.message(F.text == "🎭 ارسال میم")
async def meme_entry(message: Message, state: FSMContext, user: User, is_admin: bool, **kwargs) -> None:
    async with AsyncSessionFactory() as session:
        settings = SettingsService(session)
        locked = await settings.get_bool("bot_locked")

    if locked and not is_admin:
        await message.answer("🔒 ربات در حال حاضر قفل است. لطفاً بعداً امتحان کنید.")
        return

    async with AsyncSessionFactory() as session:
        user_svc = UserService(session)
        fresh = await user_svc.get_by_telegram_id(user.telegram_id)
        if not fresh:
            await message.answer("خطا در بارگذاری اطلاعات.")
            return

        if not is_admin and await user_svc.is_effectively_banned(fresh):
            await message.answer("🚫 حساب شما مسدود است و امکان ارسال میم ندارید.")
            return

        if not is_admin:
            # Check daily limit
            limit = await _get_daily_limit(fresh, session)
            today_count = await _count_today_memes(fresh.id, session)
            if limit is not None and today_count >= limit:
                await message.answer(
                    f"⛔ شما به محدودیت روزانه ارسال میم ({limit} عدد) رسیده‌اید.\n"
                    "فردا دوباره تلاش کنید."
                )
                return

    await state.set_state(MemeSubmitStates.waiting_media)
    await message.answer(
        "🎭 <b>ارسال میم</b>\n\n"
        "عکس، ویدیو یا گیف خود را ارسال کنید:",
        reply_markup=cancel_kb(),
    )


async def _get_daily_limit(user: User, session) -> int | None:
    """Returns None if unlimited, otherwise the numeric limit."""
    if user.no_limit:
        return None
    if user.custom_daily_limit is not None:
        return user.custom_daily_limit
    svc = SettingsService(session)
    return await svc.get_int("daily_meme_limit", 2)


async def _count_today_memes(user_id: int, session) -> int:
    from app.repositories.meme_repo import MemeRepository
    repo = MemeRepository(session)
    today_start = now_tehran().replace(hour=0, minute=0, second=0, microsecond=0)
    return await repo.count_today_by_user(user_id, today_start.astimezone(timezone.utc))


# ── Receive media ──────────────────────────────────────────────────────────────
@router.message(MemeSubmitStates.waiting_media, F.photo | F.video | F.animation)
async def meme_receive_media(
    message: Message,
    state: FSMContext,
    user: User,
    is_admin: bool,
    bot: Bot,
    **kwargs,
) -> None:
    # Determine file type and file_id
    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
    elif message.video:
        file_id = message.video.file_id
        file_type = "video"
    elif message.animation:
        file_id = message.animation.file_id
        file_type = "gif"
    else:
        await message.answer("نوع فایل پشتیبانی نمی‌شود.")
        return

    async with AsyncSessionFactory() as session:
        meme_svc = MemeService(session)
        user_svc = UserService(session)

        # Re-check ban inside transaction
        fresh = await user_svc.get_by_telegram_id(user.telegram_id)
        if not fresh:
            return

        meme = await meme_svc.submit(
            user_id=fresh.id,
            file_id=file_id,
            file_type=file_type,
        )
        await session.commit()
        meme_id = meme.id

    await state.clear()

    await message.answer(
        "✅ میم شما دریافت شد و در صف بررسی قرار گرفت.\n"
        "پس از تایید توسط ادمین، به شما اطلاع داده می‌شود.",
        reply_markup=main_menu_kb(is_admin=is_admin),
    )

    # Forward to admin group for review
    await _send_to_admin_group(bot, message, file_id, file_type, meme_id, user, fresh.id)


async def _send_to_admin_group(
    bot: Bot,
    original_msg: Message,
    file_id: str,
    file_type: str,
    meme_id: int,
    user: User,
    db_user_id: int,
) -> None:
    if not config.admin_group_id:
        logger.warning("ADMIN_GROUP_ID not set; cannot send meme for review.")
        return

    caption = (
        f"🎭 <b>میم جدید برای بررسی</b>\n\n"
        f"👤 کاربر: {user.full_name}"
        f"{' (@' + user.username + ')' if user.username else ''}\n"
        f"🆔 آیدی: <code>{user.telegram_id}</code>\n"
        f"📋 شناسه میم: <code>{meme_id}</code>"
    )

    try:
        if file_type == "photo":
            sent = await bot.send_photo(
                config.admin_group_id,
                photo=file_id,
                caption=caption,
                reply_markup=meme_review_kb(meme_id),
            )
        elif file_type == "video":
            sent = await bot.send_video(
                config.admin_group_id,
                video=file_id,
                caption=caption,
                reply_markup=meme_review_kb(meme_id),
            )
        else:  # gif
            sent = await bot.send_animation(
                config.admin_group_id,
                animation=file_id,
                caption=caption,
                reply_markup=meme_review_kb(meme_id),
            )

        # Save reviewer_message_id
        async with AsyncSessionFactory() as session:
            from app.repositories.meme_repo import MemeRepository
            repo = MemeRepository(session)
            meme = await repo.get_by_id(meme_id)
            if meme:
                meme.reviewer_message_id = sent.message_id
                await session.commit()

    except Exception as exc:
        logger.error("Failed to send meme to admin group: %s", exc)


@router.message(MemeSubmitStates.waiting_media)
async def meme_wrong_type(message: Message, **kwargs) -> None:
    await message.answer(
        "⚠️ لطفاً فقط عکس، ویدیو یا گیف ارسال کنید."
    )