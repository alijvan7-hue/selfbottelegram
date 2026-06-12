from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.core.config import config
from app.core.database import AsyncSessionFactory
from app.services.log_service import LogService
from app.services.meme_service import MemeService
from app.services.queue_service import QueueService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService

router = Router(name="meme_moderation")
logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


# ── Approve ────────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("meme_approve:"))
async def meme_approve_callback(callback: CallbackQuery, bot: Bot, **kwargs) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return

    meme_id = int(callback.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        meme_svc = MemeService(session)
        user_svc = UserService(session)
        queue_svc = QueueService(session)
        log_svc = LogService(session, bot)
        settings_svc = SettingsService(session)

        meme = await meme_svc.get_by_id(meme_id)
        if not meme:
            await callback.answer("میم یافت نشد.", show_alert=True)
            return

        if meme.status != "pending":
            await callback.answer(f"این میم قبلاً {meme.status} شده.", show_alert=True)
            return

        # Approve meme
        meme = await meme_svc.approve(meme)

        # Give token to non-admin user
        owner = await user_svc.get_by_id(meme.user_id)
        if owner and not owner.is_admin:
            await user_svc.add_tokens(owner, 1)

        # Add to publish queue
        queue_entry = await queue_svc.add_to_queue(meme_id, settings_svc)

        await session.commit()

        owner_telegram_id = owner.telegram_id if owner else None
        scheduled_time = queue_entry.scheduled_time if queue_entry else None

    # Update admin message
    try:
        await callback.message.edit_caption(
            caption=(callback.message.caption or "") + "\n\n✅ <b>تایید شد</b>",
            reply_markup=None,
        )
    except Exception:
        pass

    await callback.answer("میم تایید شد ✅")

    # Notify the user
    if owner_telegram_id:
        try:
            await bot.send_message(
                owner_telegram_id,
                "✅ <b>میم شما تایید شد!</b>\n\n"
                "میم شما وارد صف انتشار شد و به زودی منتشر خواهد شد.",
            )
        except Exception as exc:
            logger.warning("Could not notify user %s: %s", owner_telegram_id, exc)

    # Log
    async with AsyncSessionFactory() as session:
        log_svc = LogService(session, bot)
        await log_svc.log(
            event_type="meme_approved",
            description=f"میم {meme_id} تایید شد.",
            user_id=owner_telegram_id,
            admin_id=callback.from_user.id,
            extra={"meme_id": meme_id},
        )
        await session.commit()


# ── Reject ─────────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("meme_reject:"))
async def meme_reject_callback(callback: CallbackQuery, bot: Bot, **kwargs) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return

    meme_id = int(callback.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        meme_svc = MemeService(session)
        user_svc = UserService(session)

        meme = await meme_svc.get_by_id(meme_id)
        if not meme:
            await callback.answer("میم یافت نشد.", show_alert=True)
            return

        if meme.status != "pending":
            await callback.answer(f"این میم قبلاً {meme.status} شده.", show_alert=True)
            return

        meme = await meme_svc.reject(meme)
        owner = await user_svc.get_by_id(meme.user_id)
        await session.commit()

        owner_telegram_id = owner.telegram_id if owner else None

    # Update admin message
    try:
        await callback.message.edit_caption(
            caption=(callback.message.caption or "") + "\n\n❌ <b>رد شد</b>",
            reply_markup=None,
        )
    except Exception:
        pass

    await callback.answer("میم رد شد ❌")

    # Notify the user
    if owner_telegram_id:
        try:
            await bot.send_message(
                owner_telegram_id,
                "❌ <b>میم شما رد شد.</b>\n\n"
                "متأسفانه میم ارسالی شما تایید نشد. می‌توانید میم دیگری ارسال کنید.",
            )
        except Exception as exc:
            logger.warning("Could not notify user %s: %s", owner_telegram_id, exc)

    # Log
    async with AsyncSessionFactory() as session:
        log_svc = LogService(session, bot)
        await log_svc.log(
            event_type="meme_rejected",
            description=f"میم {meme_id} رد شد.",
            user_id=owner_telegram_id,
            admin_id=callback.from_user.id,
            extra={"meme_id": meme_id},
        )
        await session.commit()


# ── Admin commands: publish_now / publish_post ─────────────────────────────────
@router.message(Command("publish_now", "publish_post"))
async def cmd_publish_now(message: Message, bot: Bot, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    parts = message.text.split() if message.text else []
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("استفاده: /publish_now <meme_id>")
        return

    meme_id = int(parts[1])

    async with AsyncSessionFactory() as session:
        meme_svc = MemeService(session)
        queue_svc = QueueService(session)

        meme = await meme_svc.get_by_id(meme_id)
        if not meme:
            await message.answer("میم یافت نشد.")
            return
        if meme.status != "approved" or meme.is_published:
            await message.answer("میم قابل انتشار نیست.")
            return

        result = await queue_svc.publish_immediately(meme, bot)
        await session.commit()

    if result:
        await message.answer(f"✅ میم {meme_id} با موفقیت منتشر شد.")
    else:
        await message.answer(f"❌ انتشار میم {meme_id} با خطا مواجه شد.")


# ── Queue control ──────────────────────────────────────────────────────────────
@router.message(Command("pause_queue"))
async def cmd_pause_queue(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    async with AsyncSessionFactory() as session:
        svc = SettingsService(session)
        await svc.set("queue_paused", "true")
        await session.commit()
    await message.answer("⏸ صف انتشار متوقف شد.")


@router.message(Command("resume_queue"))
async def cmd_resume_queue(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    async with AsyncSessionFactory() as session:
        svc = SettingsService(session)
        await svc.set("queue_paused", "false")
        await session.commit()
    await message.answer("▶️ صف انتشار از سر گرفته شد.")


@router.message(Command("lock"))
async def cmd_lock(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    async with AsyncSessionFactory() as session:
        svc = SettingsService(session)
        await svc.set("bot_locked", "true")
        await session.commit()
    await message.answer("🔒 ربات قفل شد. کاربران عادی نمی‌توانند میم یا تبلیغ ثبت کنند.")


@router.message(Command("unlock"))
async def cmd_unlock(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    async with AsyncSessionFactory() as session:
        svc = SettingsService(session)
        await svc.set("bot_locked", "false")
        await session.commit()
    await message.answer("🔓 ربات قفل‌گشایی شد.")