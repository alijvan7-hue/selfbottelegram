from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
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
async def meme_approve(callback: CallbackQuery, bot: Bot, **kwargs) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return

    meme_id = int(callback.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        meme_svc = MemeService(session)
        user_svc = UserService(session)
        queue_svc = QueueService(session)
        settings_svc = SettingsService(session)
        log_svc = LogService(session, bot)

        meme = await meme_svc.get_by_id(meme_id)
        if not meme:
            await callback.answer("میم یافت نشد.", show_alert=True)
            return
        if meme.status != "pending":
            await callback.answer(f"وضعیت: {meme.status}", show_alert=True)
            return

        meme = await meme_svc.approve(meme)
        owner = await user_svc.get_by_id(meme.user_id)
        tokens_added = 0

        if owner and not owner.is_admin:
            await user_svc.add_tokens(owner, 1)
            tokens_added = 1

        queue_entry = await queue_svc.add_to_queue(meme_id, settings_svc)
        await log_svc.meme_approved(meme_id, owner.telegram_id if owner else 0, callback.from_user.id)
        await session.commit()

        owner_telegram_id = owner.telegram_id if owner else None
        owner_tokens = owner.tokens if owner else 0

    # آپدیت پیام ادمین
    try:
        original = callback.message.caption or callback.message.text or ""
        await _edit_message(callback, original + "\n\n✅ <b>تایید شد</b>")
    except Exception:
        pass

    await callback.answer("✅ تایید شد")

    # پیام به کاربر با اطلاع توکن
    if owner_telegram_id:
        try:
            await bot.send_message(
                owner_telegram_id,
                f"🎉 <b>میم شما تایید شد!</b>\n\n"
                f"🪙 <b>+{tokens_added} توکن</b> به حساب شما اضافه شد.\n"
                f"💰 موجودی فعلی: <b>{owner_tokens + tokens_added} توکن</b>\n\n"
                "میم شما وارد صف انتشار شد. به زودی در کانال منتشر می‌شود. 🚀",
            )
        except Exception as exc:
            logger.warning("اطلاع به کاربر ناموفق: %s", exc)


# ── Reject ─────────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("meme_reject:"))
async def meme_reject(callback: CallbackQuery, bot: Bot, **kwargs) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return

    meme_id = int(callback.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        meme_svc = MemeService(session)
        user_svc = UserService(session)
        log_svc = LogService(session, bot)

        meme = await meme_svc.get_by_id(meme_id)
        if not meme:
            await callback.answer("میم یافت نشد.", show_alert=True)
            return
        if meme.status != "pending":
            await callback.answer(f"وضعیت: {meme.status}", show_alert=True)
            return

        meme = await meme_svc.reject(meme)
        owner = await user_svc.get_by_id(meme.user_id)
        await log_svc.meme_rejected(meme_id, owner.telegram_id if owner else 0, callback.from_user.id)
        await session.commit()
        owner_telegram_id = owner.telegram_id if owner else None

    try:
        original = callback.message.caption or callback.message.text or ""
        await _edit_message(callback, original + "\n\n❌ <b>رد شد</b>")
    except Exception:
        pass

    await callback.answer("❌ رد شد")

    if owner_telegram_id:
        try:
            await bot.send_message(
                owner_telegram_id,
                f"😔 <b>میم شما رد شد.</b>\n\n"
                "متأسفانه محتوای ارسالی شما تایید نشد.\n"
                "می‌توانید محتوای دیگری ارسال کنید. 🎭",
            )
        except Exception:
            pass


# ── Warn (مورد دار) ────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("meme_warn:"))
async def meme_warn(callback: CallbackQuery, bot: Bot, **kwargs) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return

    meme_id = int(callback.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        meme_svc = MemeService(session)
        user_svc = UserService(session)
        log_svc = LogService(session, bot)

        meme = await meme_svc.get_by_id(meme_id)
        if not meme:
            await callback.answer("میم یافت نشد.", show_alert=True)
            return
        if meme.status != "pending":
            await callback.answer(f"وضعیت: {meme.status}", show_alert=True)
            return

        # رد میم + کم کردن 2 توکن
        meme = await meme_svc.reject(meme)
        owner = await user_svc.get_by_id(meme.user_id)
        tokens_removed = 0

        if owner and not owner.is_admin:
            await user_svc.remove_tokens(owner, 2)
            tokens_removed = 2

        await log_svc.log(
            "meme_warned",
            f"میم #{meme_id} مورد دار تشخیص داده شد. ۲ توکن کم شد.",
            user_id=owner.telegram_id if owner else 0,
            admin_id=callback.from_user.id,
        )
        await session.commit()

        owner_telegram_id = owner.telegram_id if owner else None
        owner_tokens = owner.tokens if owner else 0

    try:
        original = callback.message.caption or callback.message.text or ""
        await _edit_message(callback, original + "\n\n⚠️ <b>مورد دار — ۲ توکن کم شد</b>")
    except Exception:
        pass

    await callback.answer("⚠️ مورد دار — ۲ توکن کم شد")

    if owner_telegram_id:
        try:
            await bot.send_message(
                owner_telegram_id,
                f"⚠️ <b>هشدار!</b>\n\n"
                f"میم ارسالی شما محتوای نامناسب داشت و رد شد.\n\n"
                f"🪙 <b>-{tokens_removed} توکن</b> از حساب شما کسر شد.\n"
                f"💰 موجودی فعلی: <b>{max(0, owner_tokens - tokens_removed)} توکن</b>\n\n"
                "⚠️ توجه: تکرار این رفتار ممکن است منجر به مسدود شدن حساب شما شود.",
            )
        except Exception:
            pass


# ── Master (شاهکار) ────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("meme_master:"))
async def meme_master(callback: CallbackQuery, bot: Bot, **kwargs) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return

    meme_id = int(callback.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        meme_svc = MemeService(session)
        user_svc = UserService(session)
        queue_svc = QueueService(session)
        settings_svc = SettingsService(session)
        log_svc = LogService(session, bot)

        meme = await meme_svc.get_by_id(meme_id)
        if not meme:
            await callback.answer("میم یافت نشد.", show_alert=True)
            return
        if meme.status != "pending":
            await callback.answer(f"وضعیت: {meme.status}", show_alert=True)
            return

        # تایید + 3 توکن
        meme = await meme_svc.approve(meme)
        owner = await user_svc.get_by_id(meme.user_id)
        tokens_added = 0

        if owner and not owner.is_admin:
            await user_svc.add_tokens(owner, 3)
            tokens_added = 3

        await queue_svc.add_to_queue(meme_id, settings_svc)
        await log_svc.log(
            "meme_masterpiece",
            f"میم #{meme_id} شاهکار انتخاب شد. ۳ توکن اضافه شد.",
            user_id=owner.telegram_id if owner else 0,
            admin_id=callback.from_user.id,
        )
        await session.commit()

        owner_telegram_id = owner.telegram_id if owner else None
        owner_tokens = owner.tokens if owner else 0

    try:
        original = callback.message.caption or callback.message.text or ""
        await _edit_message(callback, original + "\n\n🌟 <b>شاهکار — ۳ توکن اضافه شد</b>")
    except Exception:
        pass

    await callback.answer("🌟 شاهکار! ۳ توکن اضافه شد")

    if owner_telegram_id:
        try:
            await bot.send_message(
                owner_telegram_id,
                f"🌟 <b>شاهکار! میم شما انتخاب ویژه شد!</b>\n\n"
                f"ادمین میم شما را به عنوان شاهکار انتخاب کرد! 🎊\n\n"
                f"🪙 <b>+{tokens_added} توکن</b> (به جای ۱ توکن معمولی) به حساب شما اضافه شد!\n"
                f"💰 موجودی فعلی: <b>{owner_tokens + tokens_added} توکن</b>\n\n"
                "میم شما وارد صف انتشار شد. 🚀",
            )
        except Exception:
            pass


# ── Publish now ────────────────────────────────────────────────────────────────
@router.message(Command("publish_now", "publish_post"))
async def cmd_publish_now(message: Message, bot: Bot, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer(
            "⚠️ <b>فرمت صحیح:</b>\n"
            "<code>/publish_now 42</code>\n\n"
            "عدد = شناسه میم"
        )
        return

    meme_id = int(parts[1])
    async with AsyncSessionFactory() as session:
        from app.services.meme_service import MemeService
        meme_svc = MemeService(session)
        queue_svc = QueueService(session)

        meme = await meme_svc.get_by_id(meme_id)
        if not meme:
            await message.answer(f"❌ میم <code>#{meme_id}</code> یافت نشد.")
            return
        if meme.status != "approved" or meme.is_published:
            await message.answer("❌ این میم قابل انتشار نیست.")
            return

        result = await queue_svc.publish_immediately(meme, bot)
        await session.commit()

    if result:
        await message.answer(f"✅ میم <code>#{meme_id}</code> منتشر شد.")
    else:
        await message.answer(f"❌ انتشار میم <code>#{meme_id}</code> ناموفق بود.")


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
    await message.answer("🔒 ربات قفل شد.")


@router.message(Command("unlock"))
async def cmd_unlock(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    async with AsyncSessionFactory() as session:
        svc = SettingsService(session)
        await svc.set("bot_locked", "false")
        await session.commit()
    await message.answer("🔓 ربات باز شد.")


async def _edit_message(callback: CallbackQuery, new_text: str) -> None:
    if callback.message.photo:
        await callback.message.edit_caption(caption=new_text, reply_markup=None)
    else:
        await callback.message.edit_text(new_text, reply_markup=None)
