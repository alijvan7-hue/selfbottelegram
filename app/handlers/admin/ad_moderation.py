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
from app.states.admin_states import AdminAdModStates
from app.utils.text_helper import fa_number

router = Router(name="ad_moderation")
logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


# ── Ad Approve ────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("ad_approve:"))
async def ad_approve_callback(callback: CallbackQuery, bot: Bot, **kwargs) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("❌ دسترسی ندارید.", show_alert=True)
        return

    ad_id = int(callback.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        ad_svc = AdService(session)
        ad = await ad_svc.get_by_id(ad_id)

        if not ad:
            await callback.answer("تبلیغ یافت نشد.", show_alert=True)
            return
        if ad.status != "pending":
            await callback.answer(f"وضعیت فعلی: {ad.status}", show_alert=True)
            return

        ad = await ad_svc.approve_ad(ad)

        from app.repositories.user_repo import UserRepository
        user_repo = UserRepository(session)
        owner = await user_repo.get_by_id(ad.user_id)
        user_telegram_id = owner.telegram_id if owner else None

        log_svc = LogService(session, bot)
        await log_svc.ad_approved(ad_id, user_telegram_id or 0, callback.from_user.id, ad.ad_type)
        await session.commit()

    # آپدیت پیام ادمین
    try:
        original = callback.message.caption or callback.message.text or ""
        new_text = original + "\n\n✅ <b>تایید شد — منتظر پرداخت کاربر</b>"
        if callback.message.photo:
            await callback.message.edit_caption(caption=new_text, reply_markup=None)
        else:
            await callback.message.edit_text(new_text, reply_markup=None)
    except Exception:
        pass

    await callback.answer("✅ تایید شد")

    # ارسال صفحه پرداخت به کاربر
    if user_telegram_id:
        from app.handlers.payment import send_payment_options
        await send_payment_options(bot, user_telegram_id, ad_id, ad)


# ── Ad Reject ─────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("ad_reject:"))
async def ad_reject_callback(callback: CallbackQuery, bot: Bot, state: FSMContext, **kwargs) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("❌ دسترسی ندارید.", show_alert=True)
        return

    ad_id = int(callback.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        ad_svc = AdService(session)
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

        log_svc = LogService(session, bot)
        await log_svc.ad_rejected(ad_id, user_telegram_id or 0, callback.from_user.id)
        await session.commit()

    # آپدیت پیام ادمین
    try:
        original = callback.message.caption or callback.message.text or ""
        new_text = original + "\n\n❌ <b>رد شد</b>"
        if callback.message.photo:
            await callback.message.edit_caption(caption=new_text, reply_markup=None)
        else:
            await callback.message.edit_text(new_text, reply_markup=None)
    except Exception:
        pass

    await callback.answer("❌ رد شد")

    # ← جدید: از ادمین دلیل رد بگیر
    await state.set_state(AdminAdModStates.waiting_reply_text)
    await state.update_data(rejected_ad_id=ad_id, rejected_user_telegram_id=user_telegram_id)
    await callback.message.answer(
        "✏️ <b>دلیل رد تبلیغ را بنویسید:</b>\n\n"
        "این پیام برای کاربر ارسال می‌شود.\n"
        "<i>مثال: تبلیغ شما به دلیل محتوای نامناسب رد شد.</i>\n\n"
        "اگر نمی‌خواهید دلیل بفرستید بنویسید: <code>skip</code>",
    )


@router.message(AdminAdModStates.waiting_reply_text, F.text)
async def receive_rejection_reason(
    message: Message, state: FSMContext, bot: Bot, **kwargs
) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    data = await state.get_data()
    user_telegram_id = data.get("rejected_user_telegram_id")
    ad_id = data.get("rejected_ad_id")
    await state.clear()

    reason = (message.text or "").strip()

    if reason.lower() != "skip" and user_telegram_id:
        try:
            await bot.send_message(
                user_telegram_id,
                f"❌ <b>تبلیغ شما (#{ad_id}) رد شد.</b>\n\n"
                f"📝 <b>دلیل:</b>\n{reason}\n\n"
                "در صورت نیاز به اطلاعات بیشتر با پشتیبانی تماس بگیرید.",
            )
            await message.answer("✅ دلیل رد برای کاربر ارسال شد.")
        except Exception as exc:
            await message.answer(f"⚠️ پیام ارسال نشد: {exc}")
    elif reason.lower() == "skip" and user_telegram_id:
        try:
            await bot.send_message(
                user_telegram_id,
                f"❌ <b>تبلیغ شما (#{ad_id}) رد شد.</b>\n\n"
                "در صورت نیاز با پشتیبانی تماس بگیرید.",
            )
        except Exception:
            pass
        await message.answer("✅ پیام رد بدون دلیل ارسال شد.")


# ── Payment Approve ───────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("pay_approve:"))
async def payment_approve_callback(
    callback: CallbackQuery, state: FSMContext, bot: Bot, **kwargs
) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("❌ دسترسی ندارید.", show_alert=True)
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

    await callback.answer("در حال پردازش...")
    await _finalize_payment_approval(callback, bot, ad_id, ad)


async def _finalize_payment_approval(
    callback: CallbackQuery, bot: Bot, ad_id: int, ad
) -> None:
    async with AsyncSessionFactory() as session:
        ad_svc = AdService(session)
        revenue_svc = RevenueService(session)
        log_svc = LogService(session, bot)

        ad = await ad_svc.get_by_id(ad_id)
        if not ad:
            return

        # reply_text از قبل در مرحله ثبت تبلیغ ذخیره شده
        ad = await ad_svc.approve_payment(ad, ad.reply_text)

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

        await log_svc.payment_approved(
            ad_id, user_telegram_id or 0,
            callback.from_user.id if callback.from_user else 0,
            ad.final_price,
        )
        await session.commit()

    # آپدیت پیام ادمین
    try:
        original = callback.message.caption or callback.message.text or ""
        new_text = original + "\n\n✅ <b>پرداخت تایید شد</b>"
        if callback.message.photo:
            await callback.message.edit_caption(caption=new_text, reply_markup=None)
        else:
            await callback.message.edit_text(new_text, reply_markup=None)
    except Exception:
        pass

    # اطلاع به کاربر
    if user_telegram_id:
        try:
            if ad.ad_type == "oneliner":
                notify = (
                    "✅ <b>پرداخت شما تایید شد.</b>\n\n"
                    "ادمین برای هماهنگی نهایی با شما در ارتباط خواهد بود."
                )
            else:
                notify = (
                    "✅ <b>پرداخت شما تایید شد!</b>\n\n"
                    "تبلیغ شما وارد صف انتشار شد و به زودی منتشر خواهد شد. 🎉"
                )
            await bot.send_message(user_telegram_id, notify)
        except Exception:
            pass


# ── Payment Reject ────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("pay_reject:"))
async def payment_reject_callback(callback: CallbackQuery, bot: Bot, **kwargs) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("❌ دسترسی ندارید.", show_alert=True)
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

        await log_svc.payment_rejected(
            ad_id, user_telegram_id or 0,
            callback.from_user.id,
        )
        await session.commit()

    try:
        original = callback.message.caption or callback.message.text or ""
        new_text = original + "\n\n❌ <b>پرداخت رد شد</b>"
        if callback.message.photo:
            await callback.message.edit_caption(caption=new_text, reply_markup=None)
        else:
            await callback.message.edit_text(new_text, reply_markup=None)
    except Exception:
        pass

    await callback.answer("❌ پرداخت رد شد")

    if user_telegram_id:
        try:
            await bot.send_message(
                user_telegram_id,
                f"❌ <b>پرداخت تبلیغ #{ad_id} رد شد.</b>\n\n"
                "احتمالاً رسید ارسالی تایید نشد.\n"
                "لطفاً با پشتیبانی تماس بگیرید.",
            )
        except Exception:
            pass
