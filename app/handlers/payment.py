from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.core.config import config
from app.core.database import AsyncSessionFactory
from app.keyboards.inline_kb import payment_options_kb, payment_review_kb
from app.keyboards.user_kb import cancel_kb, main_menu_kb
from app.models.user import User
from app.services.ad_service import AdService
from app.services.log_service import LogService
from app.services.settings_service import SettingsService
from app.states.ad_states import BannerAdStates, OnelineAdStates
from app.utils.text_helper import fa_number

router = Router(name="payment")
logger = logging.getLogger(__name__)


# ── Show payment options after ad approved ────────────────────────────────────
async def send_payment_options(bot: Bot, user_telegram_id: int, ad_id: int, ad) -> None:
    """Called by ad_moderation after admin approves an ad."""
    async with AsyncSessionFactory() as session:
        settings_svc = SettingsService(session)
        _ = settings_svc  # used below

    text = (
        f"✅ <b>تبلیغ شما تایید شد!</b>\n\n"
        f"💰 مبلغ اصلی: <b>{fa_number(ad.base_price)} تومان</b>\n"
        f"✅ مبلغ نهایی: <b>{fa_number(ad.final_price)} تومان</b>\n\n"
        "برای ادامه، کد تخفیف وارد کنید یا مستقیم پرداخت کنید:"
    )
    try:
        await bot.send_message(
            user_telegram_id,
            text,
            reply_markup=payment_options_kb(ad_id),
        )
    except Exception as exc:
        logger.error("Failed to send payment options to user %s: %s", user_telegram_id, exc)


# ── Discount code entry ───────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("discount:"))
async def discount_code_entry(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
) -> None:
    ad_id = int(callback.data.split(":")[1])
    await state.set_state(BannerAdStates.waiting_discount)
    await state.update_data(payment_ad_id=ad_id)
    await callback.message.answer(
        "🏷 <b>کد تخفیف</b>\n\nکد تخفیف خود را وارد کنید:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(BannerAdStates.waiting_discount, F.text & ~F.text.in_({"❌ انصراف"}))
async def process_discount_banner(
    message: Message,
    state: FSMContext,
    **kwargs,
) -> None:
    await _process_discount(message, state)


@router.message(OnelineAdStates.waiting_discount, F.text & ~F.text.in_({"❌ انصراف"}))
async def process_discount_oneliner(
    message: Message,
    state: FSMContext,
    **kwargs,
) -> None:
    await _process_discount(message, state)


async def _process_discount(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    ad_id = data.get("payment_ad_id")
    code = (message.text or "").strip().upper()

    from datetime import datetime, timezone
    from app.repositories.discount_repo import DiscountRepository

    async with AsyncSessionFactory() as session:
        discount_repo = DiscountRepository(session)
        dc = await discount_repo.get_valid_code(code, datetime.now(timezone.utc))

        if not dc:
            await message.answer(
                "❌ کد تخفیف نامعتبر یا منقضی شده است.\n"
                "دوباره امتحان کنید یا روی «پرداخت» بزنید."
            )
            return

        ad_svc = AdService(session)
        ad = await ad_svc.get_by_id(ad_id)
        if not ad:
            await message.answer("تبلیغ یافت نشد.")
            await state.clear()
            return

        ad = await ad_svc.apply_discount(ad, code, dc.type, dc.value)
        dc.used_count += 1
        await session.commit()

    await state.clear()
    await message.answer(
        f"✅ کد تخفیف اعمال شد!\n\n"
        f"💰 مبلغ اصلی: <b>{fa_number(ad.base_price)} تومان</b>\n"
        f"🏷 تخفیف: <b>{fa_number(ad.discount_amount)} تومان</b>\n"
        f"✅ مبلغ نهایی: <b>{fa_number(ad.final_price)} تومان</b>\n\n"
        "برای پرداخت، روی دکمه زیر بزنید:",
        reply_markup=payment_options_kb(ad_id),
    )


# ── Proceed to payment ────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("proceed_pay:"))
async def proceed_to_payment(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
) -> None:
    ad_id = int(callback.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        ad_svc = AdService(session)
        settings_svc = SettingsService(session)

        ad = await ad_svc.get_by_id(ad_id)
        if not ad:
            await callback.answer("تبلیغ یافت نشد.", show_alert=True)
            return

        card_number = await settings_svc.get("card_number") or "—"
        card_owner = await settings_svc.get("card_owner") or "—"

    await state.update_data(payment_ad_id=ad_id)
    await state.set_state(BannerAdStates.waiting_receipt)

    await callback.message.answer(
        f"💳 <b>اطلاعات پرداخت</b>\n\n"
        f"💰 مبلغ قابل پرداخت: <b>{fa_number(ad.final_price)} تومان</b>\n\n"
        f"🏦 شماره کارت:\n<code>{card_number}</code>\n\n"
        f"👤 به نام: <b>{card_owner}</b>\n\n"
        "پس از واریز، تصویر رسید را ارسال کنید:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


# ── Receive receipt (banner) ──────────────────────────────────────────────────
@router.message(BannerAdStates.waiting_receipt, F.photo)
async def receive_receipt_banner(
    message: Message,
    state: FSMContext,
    user: User,
    is_admin: bool,
    bot: Bot,
    **kwargs,
) -> None:
    await _receive_receipt(message, state, user, is_admin, bot)


# ── Receive receipt (oneliner) ────────────────────────────────────────────────
@router.message(OnelineAdStates.waiting_receipt, F.photo)
async def receive_receipt_oneliner(
    message: Message,
    state: FSMContext,
    user: User,
    is_admin: bool,
    bot: Bot,
    **kwargs,
) -> None:
    await _receive_receipt(message, state, user, is_admin, bot)


async def _receive_receipt(
    message: Message,
    state: FSMContext,
    user: User,
    is_admin: bool,
    bot: Bot,
) -> None:
    data = await state.get_data()
    ad_id = data.get("payment_ad_id")
    receipt_file_id = message.photo[-1].file_id

    async with AsyncSessionFactory() as session:
        ad_svc = AdService(session)
        log_svc = LogService(session, bot)

        ad = await ad_svc.get_by_id(ad_id)
        if not ad:
            await message.answer("تبلیغ یافت نشد.")
            await state.clear()
            return

        ad = await ad_svc.submit_payment(ad, receipt_file_id)
        await session.commit()

        await log_svc.log(
            event_type="payment_receipt_submitted",
            description=f"رسید پرداخت تبلیغ {ad_id} توسط کاربر {user.telegram_id} ارسال شد.",
            user_id=user.telegram_id,
            extra={"ad_id": ad_id},
        )
        await session.commit()

    await state.clear()
    await message.answer(
        "✅ رسید پرداخت شما دریافت شد.\n"
        "پس از تایید توسط ادمین، به شما اطلاع داده می‌شود.",
        reply_markup=main_menu_kb(is_admin=is_admin),
    )

    await _send_receipt_to_admin(bot, user, ad_id, ad, receipt_file_id)


async def _send_receipt_to_admin(
    bot: Bot,
    user: User,
    ad_id: int,
    ad,
    receipt_file_id: str,
) -> None:
    if not config.admin_group_id:
        return

    caption = (
        f"🧾 <b>رسید پرداخت تبلیغ</b>\n\n"
        f"👤 {user.full_name}"
        f"{' (@' + user.username + ')' if user.username else ''}\n"
        f"🆔 <code>{user.telegram_id}</code>\n"
        f"📋 شناسه تبلیغ: <code>{ad_id}</code>\n"
        f"📌 نوع: {'بنری' if ad.ad_type == 'banner' else 'تک خطی'}\n\n"
        f"💰 مبلغ اصلی: {fa_number(ad.base_price)} تومان\n"
        f"🏷 تخفیف: {fa_number(ad.discount_amount)} تومان\n"
        f"✅ مبلغ نهایی: {fa_number(ad.final_price)} تومان"
    )

    try:
        await bot.send_photo(
            config.admin_group_id,
            photo=receipt_file_id,
            caption=caption,
            reply_markup=payment_review_kb(ad_id),
        )
    except Exception as exc:
        logger.error("Failed to send receipt to admin: %s", exc)


@router.message(BannerAdStates.waiting_receipt)
@router.message(OnelineAdStates.waiting_receipt)
async def receipt_wrong_type(message: Message, **kwargs) -> None:
    await message.answer("⚠️ لطفاً تصویر رسید را ارسال کنید.")