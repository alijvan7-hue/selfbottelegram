from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.core.config import config
from app.core.database import AsyncSessionFactory
from app.keyboards.inline_kb import ad_review_kb
from app.keyboards.user_kb import (
    cancel_kb,
    duration_kb,
    main_menu_kb,
)
from app.models.user import User
from app.services.ad_service import AdService
from app.services.log_service import LogService
from app.services.settings_service import SettingsService
from app.states.ad_states import OnelineAdStates
from app.utils.text_helper import fa_number
from app.utils.validators import is_valid_url

router = Router(name="oneliner_ads")
logger = logging.getLogger(__name__)

_DURATION_DISCOUNTS = {7: 0, 14: 10, 21: 20, 30: 30}


# ── Entry ──────────────────────────────────────────────────────────────────────
@router.message(F.text == "📢 تبلیغات تک خطی")
async def oneliner_entry(
    message: Message,
    state: FSMContext,
    user: User,
    is_admin: bool,
    **kwargs,
) -> None:
    async with AsyncSessionFactory() as session:
        settings_svc = SettingsService(session)

        locked = await settings_svc.get_bool("bot_locked")
        if locked and not is_admin:
            await message.answer("🔒 ربات در حال حاضر قفل است.")
            return

        ad_svc = AdService(session)
        allowed, seconds_left = await ad_svc.check_ad_spam_limit(user.id, settings_svc)

        if not allowed:
            hours = seconds_left // 3600
            minutes = (seconds_left % 3600) // 60
            await message.answer(
                f"⛔ شما به محدودیت ثبت تبلیغ رسیده‌اید.\n"
                f"لطفاً {hours} ساعت و {minutes} دقیقه دیگر امتحان کنید."
            )
            return

        price = await settings_svc.get_float("oneliner_ad_price", 30000)
        sample_image = await settings_svc.get("oneliner_sample_image")
        description = await settings_svc.get("oneliner_description") or ""

    await state.set_state(OnelineAdStates.waiting_text)
    await state.update_data(base_price=price)

    intro_text = (
        f"📢 <b>تبلیغات تک خطی</b>\n\n"
        f"{description}\n\n"
        f"💰 قیمت پایه: <b>{fa_number(price)} تومان</b>\n\n"
        "مدت‌های تخفیف:\n"
        "• 7 روز — بدون تخفیف\n"
        "• 14 روز — 10٪ تخفیف\n"
        "• 21 روز — 20٪ تخفیف\n"
        "• 30 روز — 30٪ تخفیف\n\n"
        "✏️ متن تبلیغ خود را ارسال کنید:\n"
        "<i>مثال: فیلترشکن نت ملی ☄</i>"
    )

    try:
        if sample_image:
            await message.answer_photo(
                photo=sample_image,
                caption=intro_text,
                reply_markup=cancel_kb(),
            )
        else:
            await message.answer(intro_text, reply_markup=cancel_kb())
    except Exception:
        await message.answer(intro_text, reply_markup=cancel_kb())


# ── Step 1: Text ───────────────────────────────────────────────────────────────
@router.message(OnelineAdStates.waiting_text, F.text & ~F.text.in_({"❌ انصراف"}))
async def oneliner_get_text(message: Message, state: FSMContext, **kwargs) -> None:
    if not message.text:
        await message.answer("لطفاً متن تبلیغ را ارسال کنید.")
        return
    await state.update_data(ad_text=message.text)
    await state.set_state(OnelineAdStates.waiting_link)
    await message.answer(
        "🔗 لینک تبلیغ را ارسال کنید:\n"
        "<i>مثال: https://t.me/Teriak18</i>",
        reply_markup=cancel_kb(),
    )


# ── Step 2: Link ───────────────────────────────────────────────────────────────
@router.message(OnelineAdStates.waiting_link, F.text & ~F.text.in_({"❌ انصراف"}))
async def oneliner_get_link(message: Message, state: FSMContext, **kwargs) -> None:
    link = (message.text or "").strip()
    if not is_valid_url(link):
        await message.answer("⚠️ لینک نامعتبر است. لطفاً یک لینک معتبر ارسال کنید.")
        return
    await state.update_data(ad_link=link)
    await state.set_state(OnelineAdStates.waiting_duration)
    await message.answer(
        "⏳ مدت تبلیغ را انتخاب کنید:",
        reply_markup=duration_kb(),
    )


@router.message(OnelineAdStates.waiting_link)
async def oneliner_link_invalid(message: Message, **kwargs) -> None:
    await message.answer("لطفاً یک لینک معتبر ارسال کنید.")


# ── Step 3: Duration ───────────────────────────────────────────────────────────
@router.message(
    OnelineAdStates.waiting_duration,
    F.text.in_({"7 روز", "14 روز", "21 روز", "30 روز"}),
)
async def oneliner_get_duration(
    message: Message,
    state: FSMContext,
    user: User,
    is_admin: bool,
    bot: Bot,
    **kwargs,
) -> None:
    duration_map = {"7 روز": 7, "14 روز": 14, "21 روز": 21, "30 روز": 30}
    days = duration_map[message.text]
    discount_pct = _DURATION_DISCOUNTS[days]

    data = await state.get_data()
    base_price: float = data.get("base_price", 30000.0)
    total_base = base_price * days / 7  # price per week × weeks
    discount_amount = total_base * discount_pct / 100
    final_price = total_base - discount_amount

    await state.update_data(
        duration_days=days,
        discount_pct=discount_pct,
        total_base=total_base,
        discount_amount=discount_amount,
        final_price=final_price,
    )

    data = await state.get_data()
    summary = (
        f"📢 <b>خلاصه تبلیغ تک خطی</b>\n\n"
        f"📝 متن: {data['ad_text']}\n"
        f"🔗 لینک: {data['ad_link']}\n"
        f"⏳ مدت: {days} روز\n\n"
        f"💰 قیمت پایه: {fa_number(total_base)} تومان\n"
    )
    if discount_pct > 0:
        summary += (
            f"🏷 تخفیف ({discount_pct}٪): -{fa_number(discount_amount)} تومان\n"
            f"✅ مبلغ نهایی: <b>{fa_number(final_price)} تومان</b>"
        )
    else:
        summary += f"✅ مبلغ نهایی: <b>{fa_number(final_price)} تومان</b>"

    await state.set_state(OnelineAdStates.confirm)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ تایید و ارسال", callback_data="oneliner_confirm_yes"),
        InlineKeyboardButton(text="❌ انصراف", callback_data="oneliner_confirm_no"),
    )
    await message.answer(summary, reply_markup=builder.as_markup())


@router.message(OnelineAdStates.waiting_duration)
async def oneliner_duration_invalid(message: Message, **kwargs) -> None:
    await message.answer("لطفاً یکی از گزینه‌های مدت را انتخاب کنید.")


# ── Confirm ────────────────────────────────────────────────────────────────────
from aiogram.types import CallbackQuery


@router.callback_query(OnelineAdStates.confirm, F.data == "oneliner_confirm_yes")
async def oneliner_confirmed(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    is_admin: bool,
    bot: Bot,
    **kwargs,
) -> None:
    data = await state.get_data()

    async with AsyncSessionFactory() as session:
        ad_svc = AdService(session)
        log_svc = LogService(session, bot)

        ad = await ad_svc.create_oneliner_ad(
            user_id=user.id,
            text=data["ad_text"],
            link=data["ad_link"],
            duration_days=data["duration_days"],
            base_price=data["total_base"],
            discount_amount=data["discount_amount"],
            final_price=data["final_price"],
        )
        await ad_svc.increment_ad_counter(user.id)
        await session.commit()
        ad_id = ad.id

    await state.clear()
    await callback.message.edit_text(
        "✅ تبلیغ شما ثبت شد و برای بررسی ادمین ارسال شد.\n"
        "پس از تایید، مراحل پرداخت به شما نمایش داده می‌شود."
    )

    await _send_oneliner_to_admin(bot, user, ad_id, data)

    async with AsyncSessionFactory() as session:
        log_svc = LogService(session, bot)
        await log_svc.log(
            event_type="ad_submitted",
            description=f"تبلیغ تک‌خطی {ad_id} توسط کاربر {user.telegram_id} ثبت شد.",
            user_id=user.telegram_id,
            extra={"ad_id": ad_id, "type": "oneliner"},
        )
        await session.commit()

    await callback.answer()


@router.callback_query(OnelineAdStates.confirm, F.data == "oneliner_confirm_no")
async def oneliner_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    is_admin: bool,
    **kwargs,
) -> None:
    await state.clear()
    await callback.message.edit_text("عملیات لغو شد.")
    await callback.answer()


async def _send_oneliner_to_admin(
    bot: Bot,
    user: User,
    ad_id: int,
    data: dict,
) -> None:
    if not config.admin_group_id:
        return

    caption = (
        f"📢 <b>تبلیغ تک خطی جدید</b>\n\n"
        f"👤 {user.full_name}"
        f"{' (@' + user.username + ')' if user.username else ''}\n"
        f"🆔 <code>{user.telegram_id}</code>\n"
        f"📋 شناسه: <code>{ad_id}</code>\n\n"
        f"📝 متن: {data['ad_text']}\n"
        f"🔗 لینک: {data['ad_link']}\n"
        f"⏳ مدت: {data['duration_days']} روز\n\n"
        f"💰 قیمت پایه: {fa_number(data['total_base'])} تومان\n"
        f"🏷 تخفیف: {fa_number(data['discount_amount'])} تومان\n"
        f"✅ مبلغ نهایی: {fa_number(data['final_price'])} تومان"
    )

    try:
        sent = await bot.send_message(
            config.admin_group_id,
            text=caption,
            reply_markup=ad_review_kb(ad_id),
        )
        async with AsyncSessionFactory() as session:
            from app.repositories.ad_repo import AdRepository
            repo = AdRepository(session)
            ad = await repo.get_by_id(ad_id)
            if ad:
                ad.reviewer_message_id = sent.message_id
                await session.commit()
    except Exception as exc:
        logger.error("Failed to send oneliner ad to admin: %s", exc)