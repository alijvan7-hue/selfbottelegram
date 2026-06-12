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
    duration_banner_kb,
    main_menu_kb,
    skip_cancel_kb,
    yes_no_kb,
)
from app.models.user import User
from app.services.ad_service import AdService
from app.services.settings_service import SettingsService
from app.states.ad_states import BannerAdStates
from app.utils.text_helper import fa_number

router = Router(name="banner_ads")
logger = logging.getLogger(__name__)

# قیمت‌های پیش‌فرض تایم‌بندی
_DURATION_PRICES = {12: "banner_price_12h", 24: "banner_price_24h", 72: "banner_price_72h"}
_DURATION_LABELS = {12: "۱۲ ساعته", 24: "۲۴ ساعته", 72: "۷۲ ساعته"}


# ── Entry ──────────────────────────────────────────────────────────────────────
@router.message(F.text == "📢 تبلیغات بنری")
async def banner_entry(
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
            mins = (seconds_left % 3600) // 60
            await message.answer(
                f"⛔ به محدودیت ثبت تبلیغ رسیده‌اید.\n"
                f"⏳ {hours} ساعت و {mins} دقیقه دیگر امتحان کنید."
            )
            return

        # دریافت قیمت‌ها از settings
        price_12 = await settings_svc.get_float("banner_price_12h", 50000)
        price_24 = await settings_svc.get_float("banner_price_24h", 80000)
        price_72 = await settings_svc.get_float("banner_price_72h", 150000)
        reply_price = await settings_svc.get_float("banner_reply_price", 20000)
        pin_price = await settings_svc.get_float("banner_pin_price", 30000)

    await state.set_state(BannerAdStates.waiting_text)
    await state.update_data(
        price_12=price_12,
        price_24=price_24,
        price_72=price_72,
        reply_price=reply_price,
        pin_price=pin_price,
    )

    await message.answer(
        "📢 <b>ثبت تبلیغ بنری</b>\n\n"
        "💰 <b>تعرفه‌ها:</b>\n"
        f"⏱ ۱۲ ساعته: {fa_number(price_12)} تومان\n"
        f"⏱ ۲۴ ساعته: {fa_number(price_24)} تومان\n"
        f"⏱ ۷۲ ساعته: {fa_number(price_72)} تومان\n\n"
        f"💬 ریپلای خودکار: +{fa_number(reply_price)} تومان\n"
        f"📌 پین پیام: +{fa_number(pin_price)} تومان\n\n"
        "📝 <b>متن تبلیغ خود را ارسال کنید:</b>",
        reply_markup=cancel_kb(),
    )


# ── Step 1: Text ───────────────────────────────────────────────────────────────
@router.message(BannerAdStates.waiting_text, F.text & ~F.text.in_({"❌ انصراف"}))
async def banner_get_text(message: Message, state: FSMContext, **kwargs) -> None:
    await state.update_data(ad_text=message.text)
    await state.set_state(BannerAdStates.waiting_image)
    await message.answer(
        "🖼 عکس تبلیغ را ارسال کنید:\n"
        "<i>(اختیاری — برای رد کردن روی «رد کردن» بزنید)</i>",
        reply_markup=skip_cancel_kb(),
    )


# ── Step 2: Image ──────────────────────────────────────────────────────────────
@router.message(BannerAdStates.waiting_image, F.photo)
async def banner_get_image(message: Message, state: FSMContext, **kwargs) -> None:
    await state.update_data(image_file_id=message.photo[-1].file_id)
    await state.set_state(BannerAdStates.waiting_extra)
    await message.answer(
        "📋 توضیحات اضافه را ارسال کنید:\n"
        "<i>(اختیاری)</i>",
        reply_markup=skip_cancel_kb(),
    )


@router.message(BannerAdStates.waiting_image, F.text == "⏭ رد کردن")
async def banner_skip_image(message: Message, state: FSMContext, **kwargs) -> None:
    await state.update_data(image_file_id=None)
    await state.set_state(BannerAdStates.waiting_extra)
    await message.answer(
        "📋 توضیحات اضافه را ارسال کنید:\n<i>(اختیاری)</i>",
        reply_markup=skip_cancel_kb(),
    )


@router.message(BannerAdStates.waiting_image)
async def banner_image_wrong(message: Message, **kwargs) -> None:
    await message.answer("⚠️ لطفاً عکس ارسال کنید یا روی «رد کردن» بزنید.")


# ── Step 3: Extra ──────────────────────────────────────────────────────────────
@router.message(BannerAdStates.waiting_extra, F.text == "⏭ رد کردن")
async def banner_skip_extra(message: Message, state: FSMContext, **kwargs) -> None:
    await state.update_data(extra_description=None)
    await _ask_duration(message, state)


@router.message(BannerAdStates.waiting_extra, F.text & ~F.text.in_({"❌ انصراف"}))
async def banner_get_extra(message: Message, state: FSMContext, **kwargs) -> None:
    await state.update_data(extra_description=message.text)
    await _ask_duration(message, state)


@router.message(BannerAdStates.waiting_extra)
async def banner_extra_wrong(message: Message, **kwargs) -> None:
    await message.answer("لطفاً متن ارسال کنید یا روی «رد کردن» بزنید.")


# ── Step 4: Duration ───────────────────────────────────────────────────────────
async def _ask_duration(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(BannerAdStates.waiting_duration)
    await message.answer(
        "⏱ <b>مدت نمایش تبلیغ را انتخاب کنید:</b>\n\n"
        f"• ۱۲ ساعته: {fa_number(data['price_12'])} تومان\n"
        f"• ۲۴ ساعته: {fa_number(data['price_24'])} تومان\n"
        f"• ۷۲ ساعته: {fa_number(data['price_72'])} تومان",
        reply_markup=duration_banner_kb(),
    )


@router.message(
    BannerAdStates.waiting_duration,
    F.text.in_({"⏱ ۱۲ ساعته", "⏱ ۲۴ ساعته", "⏱ ۷۲ ساعته"}),
)
async def banner_get_duration(message: Message, state: FSMContext, **kwargs) -> None:
    duration_map = {"⏱ ۱۲ ساعته": 12, "⏱ ۲۴ ساعته": 24, "⏱ ۷۲ ساعته": 72}
    hours = duration_map[message.text]
    data = await state.get_data()
    price_key = f"price_{hours // (24 if hours >= 24 else 1)}{'h' if hours < 24 else 'h'}"
    # ساده‌تر:
    prices = {12: data["price_12"], 24: data["price_24"], 72: data["price_72"]}
    base_price = prices[hours]

    await state.update_data(duration_hours=hours, base_price=base_price)
    await state.set_state(BannerAdStates.waiting_reply_choice)
    await message.answer(
        f"✅ مدت انتخاب شد: <b>{_DURATION_LABELS[hours]}</b>\n"
        f"💰 قیمت پایه: {fa_number(base_price)} تومان\n\n"
        f"💬 <b>آیا ریپلای خودکار می‌خواهید؟</b>\n"
        f"<i>(+{fa_number(data['reply_price'])} تومان)</i>\n\n"
        "ریپلای خودکار: بین ۱۰ تا ۱۵ دقیقه بعد از انتشار، یک پیام روی تبلیغ شما ریپلای می‌شود.",
        reply_markup=yes_no_kb(),
    )


@router.message(BannerAdStates.waiting_duration)
async def banner_duration_wrong(message: Message, **kwargs) -> None:
    await message.answer("⚠️ لطفاً یکی از گزینه‌های زمانی را انتخاب کنید.")


# ── Step 5: Reply choice ───────────────────────────────────────────────────────
@router.message(BannerAdStates.waiting_reply_choice, F.text.in_({"✅ بله", "❌ خیر"}))
async def banner_reply_choice(message: Message, state: FSMContext, **kwargs) -> None:
    wants_reply = message.text == "✅ بله"
    await state.update_data(wants_reply=wants_reply)
    await state.set_state(BannerAdStates.waiting_pin_choice)

    data = await state.get_data()
    await message.answer(
        f"📌 <b>آیا پین پیام می‌خواهید؟</b>\n"
        f"<i>(+{fa_number(data['pin_price'])} تومان)</i>\n\n"
        "پین: پیام تبلیغ شما در بالای کانال پین می‌شود.",
        reply_markup=yes_no_kb(),
    )


@router.message(BannerAdStates.waiting_reply_choice)
async def banner_reply_wrong(message: Message, **kwargs) -> None:
    await message.answer("⚠️ لطفاً «✅ بله» یا «❌ خیر» را انتخاب کنید.")


# ── Step 6: Pin choice ─────────────────────────────────────────────────────────
@router.message(BannerAdStates.waiting_pin_choice, F.text.in_({"✅ بله", "❌ خیر"}))
async def banner_pin_choice(
    message: Message,
    state: FSMContext,
    user: User,
    is_admin: bool,
    bot: Bot,
    **kwargs,
) -> None:
    wants_pin = message.text == "✅ بله"
    await state.update_data(wants_pin=wants_pin)
    data = await state.get_data()

    # محاسبه قیمت نهایی
    base_price = data["base_price"]
    reply_price = data["reply_price"] if data.get("wants_reply") else 0
    pin_price_val = data["pin_price"] if wants_pin else 0
    total_price = base_price + reply_price + pin_price_val

    await state.update_data(
        final_price=total_price,
        reply_price_applied=reply_price,
        pin_price_applied=pin_price_val,
    )

    # نمایش خلاصه
    summary = (
        f"📋 <b>خلاصه تبلیغ بنری</b>\n\n"
        f"📝 متن: {data['ad_text'][:100]}{'...' if len(data['ad_text']) > 100 else ''}\n"
        f"🖼 عکس: {'✅ دارد' if data.get('image_file_id') else '❌ ندارد'}\n"
        f"📋 توضیحات: {'✅ دارد' if data.get('extra_description') else '❌ ندارد'}\n"
        f"⏱ مدت: {_DURATION_LABELS[data['duration_hours']]}\n"
        f"💬 ریپلای: {'✅ بله' if data.get('wants_reply') else '❌ خیر'}\n"
        f"📌 پین: {'✅ بله' if wants_pin else '❌ خیر'}\n\n"
        f"💰 <b>قیمت‌ها:</b>\n"
        f"  • پایه: {fa_number(base_price)} تومان\n"
    )
    if reply_price > 0:
        summary += f"  • ریپلای: +{fa_number(reply_price)} تومان\n"
    if pin_price_val > 0:
        summary += f"  • پین: +{fa_number(pin_price_val)} تومان\n"
    summary += f"\n✅ <b>مبلغ نهایی: {fa_number(total_price)} تومان</b>"

    # ثبت تبلیغ
    async with AsyncSessionFactory() as session:
        ad_svc = AdService(session)
        ad = await ad_svc.create_banner_ad(
            user_id=user.id,
            text=data["ad_text"],
            image_file_id=data.get("image_file_id"),
            extra_description=data.get("extra_description"),
            duration_hours=data["duration_hours"],
            wants_reply=data.get("wants_reply", False),
            wants_pin=wants_pin,
            base_price=base_price,
            reply_price=reply_price,
            pin_price=pin_price_val,
            final_price=total_price,
        )
        await ad_svc.increment_ad_counter(user.id)
        await session.commit()
        ad_id = ad.id

    await state.clear()

    await message.answer(
        f"{summary}\n\n"
        "✅ <b>تبلیغ شما ثبت شد!</b>\n"
        "پس از بررسی توسط ادمین، مراحل پرداخت به شما نمایش داده می‌شود.",
        reply_markup=main_menu_kb(is_admin=is_admin),
    )

    # ارسال به گروه ادمین
    await _send_to_admin_group(bot, user, ad_id, data, wants_pin, total_price, base_price, reply_price, pin_price_val)


@router.message(BannerAdStates.waiting_pin_choice)
async def banner_pin_wrong(message: Message, **kwargs) -> None:
    await message.answer("⚠️ لطفاً «✅ بله» یا «❌ خیر» را انتخاب کنید.")


async def _send_to_admin_group(
    bot: Bot,
    user: User,
    ad_id: int,
    data: dict,
    wants_pin: bool,
    total_price: float,
    base_price: float,
    reply_price: float,
    pin_price_val: float,
) -> None:
    if not config.admin_group_id:
        logger.warning("ADMIN_GROUP_ID تنظیم نشده!")
        return

    caption = (
        f"📢 <b>تبلیغ بنری جدید — بررسی لازم است</b>\n"
        f"{'─' * 30}\n"
        f"👤 کاربر: <b>{user.full_name}</b>"
        f"{f' (@{user.username})' if user.username else ''}\n"
        f"🆔 آیدی: <code>{user.telegram_id}</code>\n"
        f"📋 شناسه تبلیغ: <code>#{ad_id}</code>\n"
        f"{'─' * 30}\n"
        f"📝 <b>متن تبلیغ:</b>\n{data['ad_text']}\n"
    )

    if data.get("extra_description"):
        caption += f"\n📋 <b>توضیحات:</b>\n{data['extra_description']}\n"

    caption += (
        f"\n{'─' * 30}\n"
        f"⏱ مدت: <b>{_DURATION_LABELS[data['duration_hours']]}</b>\n"
        f"💬 ریپلای: {'✅ بله' if data.get('wants_reply') else '❌ خیر'}\n"
        f"📌 پین: {'✅ بله' if wants_pin else '❌ خیر'}\n"
        f"{'─' * 30}\n"
        f"💰 قیمت پایه: {fa_number(base_price)} تومان\n"
    )
    if reply_price > 0:
        caption += f"💬 ریپلای: +{fa_number(reply_price)} تومان\n"
    if pin_price_val > 0:
        caption += f"📌 پین: +{fa_number(pin_price_val)} تومان\n"
    caption += f"✅ <b>مبلغ نهایی: {fa_number(total_price)} تومان</b>"

    try:
        if data.get("image_file_id"):
            sent = await bot.send_photo(
                config.admin_group_id,
                photo=data["image_file_id"],
                caption=caption,
                reply_markup=ad_review_kb(ad_id),
            )
        else:
            sent = await bot.send_message(
                config.admin_group_id,
                text=caption,
                reply_markup=ad_review_kb(ad_id),
            )

        # ذخیره reviewer_message_id
        async with AsyncSessionFactory() as session:
            from app.repositories.ad_repo import AdRepository
            repo = AdRepository(session)
            ad = await repo.get_by_id(ad_id)
            if ad:
                ad.reviewer_message_id = sent.message_id
                await session.commit()

        logger.info("تبلیغ #%s به گروه ادمین ارسال شد.", ad_id)

    except Exception as exc:
        logger.error("خطا در ارسال تبلیغ به گروه ادمین: %s", exc)