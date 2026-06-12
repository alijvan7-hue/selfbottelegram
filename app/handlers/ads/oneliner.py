from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.core.config import config
from app.core.database import AsyncSessionFactory
from app.keyboards.inline_kb import ad_review_kb
from app.keyboards.user_kb import (
    cancel_kb,
    duration_oneliner_kb,
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
            h = seconds_left // 3600
            m = (seconds_left % 3600) // 60
            await message.answer(
                f"⛔ به محدودیت ثبت تبلیغ رسیده‌اید.\n"
                f"⏳ {h} ساعت و {m} دقیقه دیگر امتحان کنید."
            )
            return

        # قیمت هفتگی پایه
        weekly_price = await settings_svc.get_float("oneliner_ad_price", 30000)
        sample_image = await settings_svc.get("oneliner_sample_image")
        description = await settings_svc.get("oneliner_description") or ""

    await state.set_state(OnelineAdStates.waiting_text)
    await state.update_data(weekly_price=weekly_price, discount_applied=False)

    intro = (
        f"📢 <b>تبلیغات تک خطی</b>\n\n"
        f"{description}\n\n"
        f"💰 <b>تعرفه (بر اساس ۷ روز = {fa_number(weekly_price)} تومان):</b>\n"
        f"• 7 روز — {fa_number(weekly_price)} تومان\n"
        f"• 14 روز — {fa_number(weekly_price * 2 * 0.90)} تومان (10٪ تخفیف)\n"
        f"• 21 روز — {fa_number(weekly_price * 3 * 0.80)} تومان (20٪ تخفیف)\n"
        f"• 30 روز — {fa_number(weekly_price * 4.3 * 0.70)} تومان (30٪ تخفیف)\n\n"
        "✏️ <b>متن تبلیغ خود را ارسال کنید:</b>\n"
        "<i>مثال: فیلترشکن نت ملی ☄</i>"
    )

    try:
        if sample_image:
            await message.answer_photo(
                photo=sample_image,
                caption=intro,
                reply_markup=cancel_kb(),
            )
        else:
            await message.answer(intro, reply_markup=cancel_kb())
    except Exception:
        await message.answer(intro, reply_markup=cancel_kb())


# ── Step 1: Text ───────────────────────────────────────────────────────────────
@router.message(OnelineAdStates.waiting_text, F.text & ~F.text.in_({"❌ انصراف"}))
async def oneliner_get_text(message: Message, state: FSMContext, **kwargs) -> None:
    await state.update_data(ad_text=message.text)
    await state.set_state(OnelineAdStates.waiting_link)
    await message.answer(
        "🔗 <b>لینک تبلیغ را ارسال کنید:</b>\n"
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

    data = await state.get_data()
    wp = data["weekly_price"]

    await message.answer(
        "⏳ <b>مدت تبلیغ را انتخاب کنید:</b>\n\n"
        f"• 7 روز — {fa_number(wp)} تومان\n"
        f"• 14 روز — {fa_number(wp * 2 * 0.90)} تومان\n"
        f"• 21 روز — {fa_number(wp * 3 * 0.80)} تومان\n"
        f"• 30 روز — {fa_number(wp * 4.3 * 0.70)} تومان",
        reply_markup=duration_oneliner_kb(),
    )


@router.message(OnelineAdStates.waiting_link)
async def oneliner_link_wrong(message: Message, **kwargs) -> None:
    await message.answer("⚠️ لینک نامعتبر. مثال: https://t.me/channel")


# ── Step 3: Duration ───────────────────────────────────────────────────────────
@router.message(
    OnelineAdStates.waiting_duration,
    F.text.in_({"7 روز", "14 روز", "21 روز", "30 روز"}),
)
async def oneliner_get_duration(
    message: Message,
    state: FSMContext,
    **kwargs,
) -> None:
    duration_map = {"7 روز": 7, "14 روز": 14, "21 روز": 21, "30 روز": 30}
    days = duration_map[message.text]
    discount_pct = _DURATION_DISCOUNTS[days]

    data = await state.get_data()
    wp = data["weekly_price"]

    # محاسبه قیمت بر اساس هفته
    weeks = days / 7
    base_price = wp * weeks
    duration_discount = base_price * (discount_pct / 100)
    price_after_duration = base_price - duration_discount

    await state.update_data(
        duration_days=days,
        base_price=base_price,
        duration_discount=duration_discount,
        duration_discount_pct=discount_pct,
        price_after_duration=price_after_duration,
        # قیمت نهایی = قیمت بعد از تخفیف مدت (کد تخفیف هنوز اعمال نشده)
        final_price=price_after_duration,
        code_discount=0.0,
        discount_code=None,
        discount_applied=False,
    )

    summary = (
        f"📢 <b>خلاصه تبلیغ تک خطی</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📝 متن: {data['ad_text']}\n"
        f"🔗 لینک: {data['ad_link']}\n"
        f"⏳ مدت: {days} روز\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 قیمت پایه: {fa_number(base_price)} تومان\n"
    )
    if discount_pct > 0:
        summary += (
            f"🏷 تخفیف مدت ({discount_pct}٪): -{fa_number(duration_discount)} تومان\n"
            f"✅ <b>مبلغ نهایی: {fa_number(price_after_duration)} تومان</b>\n"
        )
    else:
        summary += f"✅ <b>مبلغ نهایی: {fa_number(price_after_duration)} تومان</b>\n"

    await state.set_state(OnelineAdStates.confirm)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏷 کد تخفیف", callback_data="oneliner_discount"),
        InlineKeyboardButton(text="✅ تایید و ارسال", callback_data="oneliner_confirm_yes"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ انصراف", callback_data="oneliner_confirm_no"),
    )
    await message.answer(summary, reply_markup=builder.as_markup())


@router.message(OnelineAdStates.waiting_duration)
async def oneliner_duration_wrong(message: Message, **kwargs) -> None:
    await message.answer("⚠️ لطفاً یکی از گزینه‌های مدت را انتخاب کنید.")


# ── کد تخفیف ──────────────────────────────────────────────────────────────────
@router.callback_query(OnelineAdStates.confirm, F.data == "oneliner_discount")
async def oneliner_ask_discount(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
) -> None:
    data = await state.get_data()

    if data.get("discount_applied"):
        await callback.answer("⚠️ قبلاً یک کد تخفیف اعمال کردید.", show_alert=True)
        return

    await state.set_state(OnelineAdStates.waiting_discount)
    await callback.message.answer(
        "🏷 <b>کد تخفیف خود را وارد کنید:</b>",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(OnelineAdStates.waiting_discount, F.text & ~F.text.in_({"❌ انصراف"}))
async def oneliner_apply_discount(
    message: Message,
    state: FSMContext,
    **kwargs,
) -> None:
    data = await state.get_data()

    if data.get("discount_applied"):
        await message.answer("⚠️ قبلاً یک کد تخفیف اعمال کردید.")
        await state.set_state(OnelineAdStates.confirm)
        return

    code = (message.text or "").strip().upper()
    from datetime import datetime, timezone

    async with AsyncSessionFactory() as session:
        from app.repositories.discount_repo import DiscountRepository
        repo = DiscountRepository(session)
        dc = await repo.get_valid_code(code, datetime.now(timezone.utc))

        if not dc:
            await message.answer(
                "❌ کد تخفیف نامعتبر یا منقضی شده است.\n"
                "دوباره امتحان کنید."
            )
            return

        # ← تخفیف روی قیمت بعد از تخفیف مدت اعمال می‌شود
        price_after_duration = data["price_after_duration"]

        if dc.type == "percent":
            code_discount = price_after_duration * (dc.value / 100)
        else:
            code_discount = dc.value

        final_price = max(0.0, price_after_duration - code_discount)

        dc.used_count += 1
        await session.commit()

    await state.update_data(
        code_discount=code_discount,
        discount_code=code,
        final_price=final_price,
        discount_applied=True,
    )
    await state.set_state(OnelineAdStates.confirm)

    data = await state.get_data()

    summary = (
        f"✅ <b>کد تخفیف اعمال شد!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 قیمت پایه: {fa_number(data['base_price'])} تومان\n"
    )
    if data["duration_discount"] > 0:
        summary += f"🏷 تخفیف مدت ({data['duration_discount_pct']}٪): -{fa_number(data['duration_discount'])} تومان\n"

    summary += (
        f"🏷 کد <code>{code}</code>: -{fa_number(code_discount)} تومان\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ <b>مبلغ نهایی: {fa_number(final_price)} تومان</b>"
    )

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ تایید و ارسال", callback_data="oneliner_confirm_yes"),
        InlineKeyboardButton(text="❌ انصراف", callback_data="oneliner_confirm_no"),
    )
    await message.answer(summary, reply_markup=builder.as_markup())


# ── Confirm ────────────────────────────────────────────────────────────────────
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
            base_price=data["price_after_duration"],  # قیمت بعد از تخفیف مدت = قیمت پایه برای کد
            discount_amount=data.get("code_discount", 0),
            final_price=data["final_price"],
        )
        await ad_svc.increment_ad_counter(user.id)
        await session.commit()
        ad_id = ad.id

    await state.clear()
    await callback.message.edit_text(
        "✅ <b>تبلیغ ثبت شد!</b>\n"
        "پس از بررسی ادمین، مراحل پرداخت نمایش داده می‌شود."
    )

    await _send_oneliner_to_admin(bot, user, ad_id, data)

    async with AsyncSessionFactory() as session:
        log_svc = LogService(session, bot)
        await log_svc.log(
            "ad_submitted",
            f"تبلیغ تک‌خطی #{ad_id} ثبت شد.",
            user_id=user.telegram_id,
            extra={"ad_id": ad_id},
        )
        await session.commit()

    await callback.answer()


@router.callback_query(OnelineAdStates.confirm, F.data == "oneliner_confirm_no")
async def oneliner_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
) -> None:
    await state.clear()
    await callback.message.edit_text("❌ عملیات لغو شد.")
    await callback.answer()


async def _send_oneliner_to_admin(
    bot: Bot, user: User, ad_id: int, data: dict
) -> None:
    if not config.admin_group_id:
        return

    caption = (
        f"📢 <b>تبلیغ تک خطی جدید</b>\n"
        f"{'━' * 25}\n"
        f"👤 <b>{user.full_name}</b>"
        f"{f' (@{user.username})' if user.username else ''}\n"
        f"🆔 <code>{user.telegram_id}</code>\n"
        f"📋 شناسه: <code>#{ad_id}</code>\n"
        f"{'━' * 25}\n"
        f"📝 متن: {data['ad_text']}\n"
        f"🔗 لینک: {data['ad_link']}\n"
        f"⏳ مدت: {data['duration_days']} روز\n"
        f"{'━' * 25}\n"
        f"💰 قیمت پایه: {fa_number(data['base_price'])} تومان\n"
    )
    if data.get("duration_discount", 0) > 0:
        caption += f"🏷 تخفیف مدت: -{fa_number(data['duration_discount'])} تومان\n"
    if data.get("code_discount", 0) > 0:
        caption += f"🏷 کد <code>{data['discount_code']}</code>: -{fa_number(data['code_discount'])} تومان\n"

    caption += f"✅ <b>مبلغ نهایی: {fa_number(data['final_price'])} تومان</b>"

    try:
        from app.keyboards.inline_kb import ad_review_kb
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
        logger.error("خطا در ارسال به ادمین: %s", exc)
