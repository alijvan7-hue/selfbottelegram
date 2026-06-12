from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.types import Message

from app.core.config import config
from app.core.database import AsyncSessionFactory
from app.services.log_service import LogService
from app.services.settings_service import SettingsService
from app.utils.text_helper import fa_number

router = Router(name="settings_management")
logger = logging.getLogger(__name__)

_SETTING_LABELS: dict[str, str] = {
    "publish_start_hour": "ساعت شروع انتشار (0-23)",
    "publish_end_hour": "ساعت پایان انتشار (1-24)",
    "min_publish_interval": "حداقل فاصله انتشار (دقیقه)",
    "max_publish_interval": "حداکثر فاصله انتشار (دقیقه)",
    "daily_meme_limit": "محدودیت روزانه میم",
    "ad_limit_count": "تعداد تبلیغ در پنجره زمانی",
    "ad_limit_hours": "پنجره زمانی تبلیغ (ساعت)",
    "banner_price_12h": "قیمت تبلیغ بنری ۱۲ ساعته (تومان)",
    "banner_price_24h": "قیمت تبلیغ بنری ۲۴ ساعته (تومان)",
    "banner_price_72h": "قیمت تبلیغ بنری ۷۲ ساعته (تومان)",
    "banner_reply_price": "قیمت ریپلای خودکار (تومان)",
    "banner_pin_price": "قیمت پین پیام (تومان)",
    "oneliner_ad_price": "قیمت تبلیغ تک خطی (تومان)",
    "card_number": "شماره کارت",
    "card_owner": "نام صاحب کارت",
    "support_id": "آیدی پشتیبانی",
    "oneliner_description": "توضیحات تبلیغ تک خطی",
    "queue_paused": "صف متوقف (true/false)",
    "bot_locked": "ربات قفل (true/false)",
}


def _is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


@router.message(F.text == "⚙️ تنظیمات")
async def settings_btn(message: Message, is_admin: bool, **kwargs) -> None:
    if not is_admin:
        return
    await _show_settings(message)


async def _show_settings(message: Message) -> None:
    async with AsyncSessionFactory() as session:
        svc = SettingsService(session)
        all_settings = await svc.all()

    lines = ["⚙️ <b>تنظیمات سیستم</b>\n━━━━━━━━━━━━━━━\n"]

    groups = [
        ("📡 انتشار میم", ["publish_start_hour", "publish_end_hour", "min_publish_interval", "max_publish_interval", "daily_meme_limit"]),
        ("📢 تبلیغات", ["ad_limit_count", "ad_limit_hours", "banner_price_12h", "banner_price_24h", "banner_price_72h", "banner_reply_price", "banner_pin_price", "oneliner_ad_price"]),
        ("💳 پرداخت", ["card_number", "card_owner"]),
        ("📞 پشتیبانی", ["support_id"]),
        ("🔒 وضعیت", ["queue_paused", "bot_locked"]),
    ]

    for group_title, keys in groups:
        lines.append(f"\n<b>{group_title}</b>")
        for k in keys:
            val = all_settings.get(k, "—")
            label = _SETTING_LABELS.get(k, k)
            lines.append(f"  • {label}:\n    <code>{val}</code>")

    lines.append(
        "\n━━━━━━━━━━━━━━━\n"
        "✏️ برای تغییر:\n"
        "<code>/set کلید مقدار</code>\n\n"
        "مثال:\n"
        "<code>/set banner_price_24h 80000</code>\n"
        "<code>/set card_number 6037991234567890</code>"
    )

    await message.answer("\n".join(lines))


@router.message(F.text.regexp(r"^/set\s+\S+\s+.+"))
async def cmd_set_setting(message: Message, bot: Bot, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "⚠️ <b>فرمت صحیح:</b>\n"
            "<code>/set کلید مقدار</code>\n\n"
            "برای مشاهده کلیدها: <b>⚙️ تنظیمات</b>"
        )
        return

    _, key, value = parts

    if key not in _SETTING_LABELS:
        await message.answer(
            f"❌ کلید <code>{key}</code> وجود ندارد.\n\n"
            "برای مشاهده کلیدهای مجاز: <b>⚙️ تنظیمات</b>"
        )
        return

    error = _validate_setting(key, value)
    if error:
        await message.answer(f"❌ {error}")
        return

    async with AsyncSessionFactory() as session:
        svc = SettingsService(session)
        log_svc = LogService(session, bot)
        await svc.set(key, value)
        await log_svc.settings_changed(key, value, message.from_user.id)
        await session.commit()

    label = _SETTING_LABELS[key]
    await message.answer(
        f"✅ <b>{label}</b>\n"
        f"مقدار جدید: <code>{value}</code>"
    )


def _validate_setting(key: str, value: str) -> str | None:
    integer_keys = {
        "publish_start_hour", "publish_end_hour",
        "min_publish_interval", "max_publish_interval",
        "daily_meme_limit", "ad_limit_count", "ad_limit_hours",
    }
    float_keys = {
        "banner_price_12h", "banner_price_24h", "banner_price_72h",
        "banner_reply_price", "banner_pin_price", "oneliner_ad_price",
    }
    bool_keys = {"queue_paused", "bot_locked"}

    if key in integer_keys:
        if not value.isdigit():
            return f"مقدار باید عدد صحیح باشد. مثال: <code>/set {key} 10</code>"
        num = int(value)
        if key == "publish_start_hour" and not (0 <= num <= 23):
            return "ساعت شروع باید بین 0 تا 23 باشد."
        if key == "publish_end_hour" and not (1 <= num <= 24):
            return "ساعت پایان باید بین 1 تا 24 باشد."
    elif key in float_keys:
        try:
            float(value)
        except ValueError:
            return f"مقدار باید عدد باشد. مثال: <code>/set {key} 50000</code>"
    elif key in bool_keys:
        if value.lower() not in ("true", "false"):
            return f"مقدار باید <code>true</code> یا <code>false</code> باشد."

    return None


@router.message(F.photo & F.caption.startswith("/set_sample_image"))
async def set_sample_image(message: Message, bot: Bot, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    file_id = message.photo[-1].file_id
    async with AsyncSessionFactory() as session:
        svc = SettingsService(session)
        await svc.set("oneliner_sample_image", file_id)
        await session.commit()
    await message.answer("✅ عکس نمونه تبلیغ تک خطی ذخیره شد.")