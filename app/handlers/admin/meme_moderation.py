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


async def _edit_msg(callback: CallbackQuery, text: str) -> None:
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=None)
        else:
            await callback.message.edit_text(text, reply_markup=None)
    except Exception:
        pass


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

        await meme_svc.approve(meme)
        owner = await user_svc.get_by_id(meme.user_id)

        tokens_before = owner.tokens if owner else 0
        if owner and not owner.is_admin:
            await user_svc.add_tokens(owner, 1)
        tokens_after = owner.tokens if owner else 0

        await queue_svc.add_to_queue(meme_id, settings_svc)
        # بازچینی خودکار صف
        await queue_svc.reorder_queue(settings_svc)

        await log_svc.meme_approved(
            meme_id,
            owner.telegram_id if owner else 0,
            callback.from_user.id,
        )
        await session.commit()

        owner_tid = owner.telegram_id if owner else None

    original = callback.message.caption or callback.message.text or ""
    try:
        await callback.message.delete()
    except Exception:
        await _edit_msg(callback, original + "\n\n✅ <b>تایید شد</b>")
    await callback.answer("✅ تایید شد")

    if owner_tid:
        try:
            await bot.send_message(
                owner_tid,
                f"🎉 <b>میم شما تایید شد!</b>\n\n"
                f"🪙 <b>+1 توکن</b> به حساب شما اضافه شد.\n"
                f"💰 موجودی فعلی: <b>{fa_number(tokens_after)} توکن</b>\n\n"
                "میم شما وارد صف انتشار شد. به زودی در کانال منتشر می‌شود. 🚀",
            )
        except Exception as e:
            logger.warning("اطلاع به کاربر ناموفق: %s", e)


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

        await meme_svc.reject(meme)
        owner = await user_svc.get_by_id(meme.user_id)
        await log_svc.meme_rejected(
            meme_id,
            owner.telegram_id if owner else 0,
            callback.from_user.id,
        )
        await session.commit()
        owner_tid = owner.telegram_id if owner else None

    original = callback.message.caption or callback.message.text or ""
    await _edit_msg(callback, original + "\n\n❌ <b>رد شد</b>")
    await callback.answer("❌ رد شد")

    if owner_tid:
        try:
            await bot.send_message(
                owner_tid,
                "😔 <b>میم شما رد شد.</b>\n\n"
                "محتوای ارسالی تایید نشد.\n"
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

        await meme_svc.reject(meme)
        owner = await user_svc.get_by_id(meme.user_id)
        tokens_before = owner.tokens if owner else 0

        if owner and not owner.is_admin:
            await user_svc.remove_tokens(owner, 2)

        tokens_after = max(0, tokens_before - 2)

        await log_svc.log(
            "meme_warned",
            f"میم #{meme_id} مورد دار — ۲ توکن کسر شد.",
            user_id=owner.telegram_id if owner else 0,
            admin_id=callback.from_user.id,
        )
        await session.commit()
        owner_tid = owner.telegram_id if owner else None

    original = callback.message.caption or callback.message.text or ""
    await _edit_msg(callback, original + "\n\n⚠️ <b>مورد دار — ۲ توکن کسر شد</b>")
    await callback.answer("⚠️ مورد دار")

    if owner_tid:
        try:
            await bot.send_message(
                owner_tid,
                f"⚠️ <b>هشدار! محتوای نامناسب</b>\n\n"
                f"میم ارسالی شما محتوای نامناسب داشت و رد شد.\n\n"
                f"🪙 <b>-2 توکن</b> از حساب شما کسر شد.\n"
                f"💰 موجودی فعلی: <b>{fa_number(tokens_after)} توکن</b>\n\n"
                "⚠️ تکرار این رفتار منجر به مسدود شدن حساب می‌شود.",
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

        meme.is_masterpiece = True
        await meme_svc.approve(meme)
        owner = await user_svc.get_by_id(meme.user_id)
        tokens_before = owner.tokens if owner else 0

        if owner and not owner.is_admin:
            await user_svc.add_tokens(owner, 3)

        tokens_after = tokens_before + 3

        await queue_svc.add_to_queue(meme_id, settings_svc)
        await queue_svc.reorder_queue(settings_svc)

        await log_svc.log(
            "meme_masterpiece",
            f"میم #{meme_id} شاهکار — ۳ توکن اضافه شد.",
            user_id=owner.telegram_id if owner else 0,
            admin_id=callback.from_user.id,
        )
        await session.commit()
        owner_tid = owner.telegram_id if owner else None

    try:
        await callback.message.delete()
    except Exception:
        original = callback.message.caption or callback.message.text or ""
        await _edit_msg(callback, original + "\n\n🌟 <b>شاهکار — ۳ توکن اضافه شد</b>")
    await callback.answer("🌟 شاهکار!")

    if owner_tid:
        try:
            await bot.send_message(
                owner_tid,
                f"🌟 <b>شاهکار! انتخاب ویژه ادمین!</b>\n\n"
                f"ادمین میم شما را به عنوان شاهکار انتخاب کرد! 🎊\n\n"
                f"🪙 <b>+3 توکن</b> (به جای ۱ توکن معمولی)\n"
                f"💰 موجودی فعلی: <b>{fa_number(tokens_after)} توکن</b>\n\n"
                "میم شما وارد صف انتشار شد. 🚀",
            )
        except Exception:
            pass


# ── دستورات ───────────────────────────────────────────────────────────────────
@router.message(Command("publish_now", "publish_post"))
async def cmd_publish_now(message: Message, bot: Bot, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer(
            "⚠️ <b>فرمت صحیح:</b>\n<code>/publish_now 42</code>"
        )
        return
    meme_id = int(parts[1])
    async with AsyncSessionFactory() as session:
        meme_svc = MemeService(session)
        queue_svc = QueueService(session)
        meme = await meme_svc.get_by_id(meme_id)
        if not meme:
            await message.answer(f"❌ میم #{meme_id} یافت نشد.")
            return
        if meme.is_published:
            await message.answer("❌ این میم قبلاً منتشر شده.")
            return
        result = await queue_svc.publish_immediately(meme, bot)
        await session.commit()
    await message.answer(
        f"✅ میم #{meme_id} منتشر شد." if result else f"❌ انتشار ناموفق."
    )


@router.message(Command("pause_queue"))
async def cmd_pause_queue(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    async with AsyncSessionFactory() as session:
        await SettingsService(session).set("queue_paused", "true")
        await session.commit()
    await message.answer("⏸ صف متوقف شد.")


@router.message(Command("resume_queue"))
async def cmd_resume_queue(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    async with AsyncSessionFactory() as session:
        await SettingsService(session).set("queue_paused", "false")
        await session.commit()
    await message.answer("▶️ صف از سر گرفته شد.")


@router.message(Command("lock"))
async def cmd_lock(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    async with AsyncSessionFactory() as session:
        await SettingsService(session).set("bot_locked", "true")
        await session.commit()
    await message.answer("🔒 ربات قفل شد.")


@router.message(Command("unlock"))
async def cmd_unlock(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    async with AsyncSessionFactory() as session:
        await SettingsService(session).set("bot_locked", "false")
        await session.commit()
    await message.answer("🔓 ربات باز شد.")


# import داخل فایل برای جلوگیری از circular
from app.utils.text_helper import fa_number  # noqa: E402
