from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.core.config import config
from app.core.database import AsyncSessionFactory
from app.services.ad_service import AdService
from app.services.log_service import LogService
from app.services.revenue_service import RevenueService
from app.services.settings_service import SettingsService
from app.states.admin_states import AdminAdModStates
from app.utils.text_helper import fa_number

router = Router(name="ad_moderation")
logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


# ── Ad Approve ────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("ad_approve:"))
async def ad_approve_callback(
    callback: CallbackQuery,
    bot: Bot,
    **kwargs,
) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return

    ad_id = int(callback.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        ad_svc = AdService(session)
        log_svc = LogService(session, bot)

        ad = await ad_svc.get_by_id(ad_id)
        if not ad:
            await callback.answer("تبلیغ یافت نشد.", show_alert=True)
            return
        if ad.status != "pending":
            await callback.answer(f"وضعیت: {ad.status}", show_alert=True)
            return

        ad = await ad_svc.approve_ad(ad)
        await session.commit()

        user_telegram_id = None
        from app.repositories.user_repo import UserRepository
        user_repo = UserRepository(session)
        owner = await user_repo.get_by_id(ad.user_id)
        if owner:
            user_telegram_id = owner.telegram_id

        await log_svc.log(
            event_type="ad_approved",
            description=f"تبلیغ {ad_id} تایید شد.",
            user_id=user_telegram_id,
            admin_id=callback.from_user.id,
            extra={"ad_id": ad_id},
        )
        await session.commit()

    try:
        original_text = callback.message.caption or callback.message.text or ""
        edit_text = original_text + "\n\n✅ <b>تایید شد — منتظر پرداخت</b>"
        if callback.message.photo:
            await callback.message.edit_caption(caption=edit_text, reply_markup=None)
        else:
            await callback.message.edit_text(edit_text, reply_markup=None)
    except Exception:
        pass

    await callback.answer("تبلیغ تایید شد ✅")

    # Send payment options to user
    if user_telegram_id and ad:
        from app.handlers.payment import send_payment_options
        await send_payment_options(bot, user_telegram_id, ad_id, ad)


# ── Ad Reject ─────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("ad_reject:"))
async def ad_reject_callback(
    callback: CallbackQuery,
    bot: Bot,
    **kwargs,
) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return

    ad_id = int(callback.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        ad_svc = AdService(session)
        log_svc = LogService(session, bot)

        ad = await ad_svc.get_by_id(ad_id)
        if not ad:
            await callback.answer("تبلیغ یافت نشد.", show_alert=True)
            return
        if ad.status != "pending":
            await callback.answer(f"وضعیت: {ad.status}", show_alert=True)
            return

        ad = await ad_svc.reject_ad(ad)

        from app.repositories.user_repo import UserRepository
        user_repo = UserRepository(session)
        owner = await user_repo.get_by_id(ad.user_id)
        user_telegram_id = owner.telegram_id if owner else None

        await log_svc.log(
            event_type="ad_rejected",
            description=f"تبلیغ {ad_id} رد شد.",
            user_id=user_telegram_id,
            admin_id=callback.from_user.id,
            extra={"ad_id": ad_id},
        )
        await session.commit()

    try:
        original_text = callback.message.caption or callback.message.text or ""
        edit_text = original_text + "\n\n❌ <b>رد شد</b>"
        if callback.message.photo:
            await callback.message.edit_caption(caption=edit_text, reply_markup=None)
        else:
            await callback.message.edit_text(edit_text, reply_markup=None)
    except Exception:
        pass

    await callback.answer("تبلیغ رد شد ❌")

    if user_telegram_id:
        try:
            await bot.send_message(
                user_telegram_id,
                "❌ متأسفانه تبلیغ شما تایید نشد.\nلطفاً با پشتیبانی تماس بگیرید.",
            )
        except Exception:
            pass


# ── Payment Approve ───────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("pay_approve:"))
async def payment_approve_callback(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    **kwargs,
) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return

    ad_id = int(callback.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        ad_svc = AdService(session)
        ad = await ad_svc.get_by_id(ad_id)
        if not ad:
            await callback.answer("تبلیغ یافت نشد.", show_alert=True)
            return
        if ad.status != "payment_pending":
            await callback.answer(f"وضعیت: {ad.status}", show_alert=True)
            return

    # For banner ads, ask for reply text
    if ad.ad_type == "banner":
        await state.set_state(AdminAdModStates.waiting_reply_text)
        await state.update_data(approving_ad_id=ad_id)
        await callback.message.answer(
            "✏️ <b>متن ریپلای خودکار را وارد کنید:</b>\n\n"
            "این متن بین 10 تا 15 دقیقه بعد از انتشار تبلیغ به صورت خودکار ریپلای می‌شود.\n\n"
            "اگر نمی‌خواهید ریپلای داشته باشد، بنویسید: <code>skip</code>",
            reply_markup=None,
        )
        await callback.answer()
    else:
        # Oneliner: approve directly
        await _finalize_payment_approval(callback, bot, ad_id, reply_text=None)


# ── Receive reply text for banner ─────────────────────────────────────────────
@router.message(AdminAdModStates.waiting_reply_text, F.text)
async def receive_reply_text(
    message: Message,
    state: FSMContext,
    bot: Bot,
    **kwargs,
) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    data = await state.get_data()
    ad_id = data.get("approving_ad_id")
    reply_text = None if (message.text or "").strip().lower() == "skip" else message.text

    await state.clear()
    await _finalize_payment_approval_from_message(message, bot, ad_id, reply_text)


async def _finalize_payment_approval(
    callback: CallbackQuery,
    bot: Bot,
    ad_id: int,
    reply_text,
) -> None:
    async with AsyncSessionFactory() as session:
        ad_svc = AdService(session)
        log_svc = LogService(session, bot)
        revenue_svc = RevenueService(session)

        ad = await ad_svc.get_by_id(ad_id)
        if not ad:
            return

        ad = await ad_svc.approve_payment(ad, reply_text)

        from app.repositories.user_repo import UserRepository
        user_repo = UserRepository(session)
        owner = await user_repo.get_by_id(ad.user_id)
        user_telegram_id = owner.telegram_id if owner else None

        # Record revenue
        from datetime import date
        await revenue_svc.record(
            ad_id=ad.id,
            user_id=ad.user_id,
            amount=ad.final_price,
            ad_type=ad.ad_type,
            date=date.today(),
        )

        await log_svc.log(
            event_type="payment_approved",
            description=f"پرداخت تبلیغ {ad_id} تایید شد. مبلغ: {ad.final_price}",
            user_id=user_telegram_id,
            admin_id=callback.from_user.id if callback.from_user else None,
            extra={"ad_id": ad_id, "amount": ad.final_price},
        )
        await session.commit()

    try:
        original_text = callback.message.caption or callback.message.text or ""
        edit_text = original_text + "\n\n✅ <b>پرداخت تایید شد</b>"
        if callback.message.photo:
            await callback.message.edit_caption(caption=edit_text, reply_markup=None)
        else:
            await callback.message.edit_text(edit_text, reply_markup=None)
    except Exception:
        pass

    await callback.answer("پرداخت تایید شد ✅")

    if user_telegram_id:
        try:
            if ad.ad_type == "oneliner":
                notify_text = (
                    "✅ <b>پرداخت شما تایید شد.</b>\n\n"
                    "ادمین برای هماهنگی نهایی با شما در ارتباط خواهد بود."
                )
            else:
                notify_text = (
                    "✅ <b>پرداخت شما تایید شد!</b>\n\n"
                    "تبلیغ شما وارد صف انتشار شد."
                )
            await bot.send_message(user_telegram_id, notify_text)
        except Exception:
            pass


async def _finalize_payment_approval_from_message(
    message: Message,
    bot: Bot,
    ad_id: int,
    reply_text,
) -> None:
    async with AsyncSessionFactory() as session:
        ad_svc = AdService(session)
        log_svc = LogService(session, bot)
        revenue_svc = RevenueService(session)

        ad = await ad_svc.get_by_id(ad_id)
        if not ad:
            await message.answer("تبلیغ یافت نشد.")
            return

        ad = await ad_svc.approve_payment(ad, reply_text)

        from app.repositories.user_repo import UserRepository
        user_repo = UserRepository(session)
        owner = await user_repo.get_by_id(ad.user_id)
        user_telegram_id = owner.telegram_id if owner else None

        from datetime import date
        await revenue_svc.record(
            ad_id=ad.id,
            user_id=ad.user_id,
            amount=ad.final_price,
            ad_type=ad.ad_type,
            date=date.today(),
        )

        await log_svc.log(
            event_type="payment_approved",
            description=f"پرداخت تبلیغ {ad_id} تایید شد.",
            user_id=user_telegram_id,
            admin_id=message.from_user.id if message.from_user else None,
            extra={"ad_id": ad_id, "amount": ad.final_price},
        )
        await session.commit()

    await message.answer(f"✅ پرداخت تبلیغ <code>{ad_id}</code> تایید شد.")

    if user_telegram_id:
        try:
            if ad.ad_type == "oneliner":
                notify_text = (
                    "✅ <b>پرداخت شما تایید شد.</b>\n\n"
                    "ادمین برای هماهنگی نهایی با شما در ارتباط خواهد بود."
                )
            else:
                notify_text = "✅ <b>پرداخت شما تایید شد!</b>\n\nتبلیغ شما وارد صف انتشار شد."
            await bot.send_message(user_telegram_id, notify_text)
        except Exception:
            pass


# ── Payment Reject ────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("pay_reject:"))
async def payment_reject_callback(
    callback: CallbackQuery,
    bot: Bot,
    **kwargs,
) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return

    ad_id = int(callback.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        ad_svc = AdService(session)
        log_svc = LogService(session, bot)

        ad = await ad_svc.get_by_id(ad_id)
        if not ad:
            await callback.answer("تبلیغ یافت نشد.", show_alert=True)
            return

        ad = await ad_svc.reject_payment(ad)

        from app.repositories.user_repo import UserRepository
        user_repo = UserRepository(session)
        owner = await user_repo.get_by_id(ad.user_id)
        user_telegram_id = owner.telegram_id if owner else None

        await log_svc.log(
            event_type="payment_rejected",
            description=f"پرداخت تبلیغ {ad_id} رد شد.",
            user_id=user_telegram_id,
            admin_id=callback.from_user.id,
            extra={"ad_id": ad_id},
        )
        await session.commit()

    try:
        original_text = callback.message.caption or callback.message.text or ""
        edit_text = original_text + "\n\n❌ <b>پرداخت رد شد</b>"
        if callback.message.photo:
            await callback.message.edit_caption(caption=edit_text, reply_markup=None)
        else:
            await callback.message.edit_text(edit_text, reply_markup=None)
    except Exception:
        pass

    await callback.answer("پرداخت رد شد ❌")

    if user_telegram_id:
        try:
            await bot.send_message(
                user_telegram_id,
                "❌ <b>پرداخت شما رد شد.</b>\n\nلطفاً با پشتیبانی تماس بگیرید.",
            )
        except Exception:
            pass