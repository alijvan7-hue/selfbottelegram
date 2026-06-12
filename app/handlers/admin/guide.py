from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.core.config import config
from app.utils.text_helper import fa_number

router = Router(name="admin_guide")


def _is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


@router.message(F.text == "📖 راهنمای ادمین")
async def admin_guide(message: Message, is_admin: bool, **kwargs) -> None:
    if not is_admin:
        return

    text = (
        "📖 <b>راهنمای کامل ادمین</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"

        "👥 <b>مدیریت کاربران</b>\n"
        "━━━━━━━━━━━━\n"
        "🔍 اطلاعات کاربر:\n"
        "<code>/user 123456789</code>\n\n"

        "🚫 بن کاربر:\n"
        "<code>/ban 123456789 7d</code> — ۷ روز\n"
        "<code>/ban 123456789 30d</code> — ۳۰ روز\n"
        "<code>/ban 123456789 permanent</code> — دائمی\n\n"

        "✅ رفع بن:\n"
        "<code>/unban 123456789</code>\n\n"

        "🪙 افزایش توکن:\n"
        "<code>/addtoken 123456789 10</code>\n\n"

        "🪙 کاهش توکن:\n"
        "<code>/removetoken 123456789 5</code>\n\n"

        "📊 تنظیم محدودیت ارسال میم:\n"
        "<code>/setlimit 123456789 5</code> — ۵ میم در روز\n"
        "<code>/setlimit 123456789 unlimited</code> — بی‌نهایت\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 <b>مدیریت صف انتشار</b>\n"
        "━━━━━━━━━━━━\n"
        "🚀 انتشار فوری میم:\n"
        "<code>/publish_now 42</code>\n\n"

        "⏸ توقف صف:\n"
        "<code>/pause_queue</code>\n\n"

        "▶️ ادامه صف:\n"
        "<code>/resume_queue</code>\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔒 <b>قفل ربات</b>\n"
        "━━━━━━━━━━━━\n"
        "🔒 قفل کردن:\n"
        "<code>/lock</code>\n\n"

        "🔓 باز کردن:\n"
        "<code>/unlock</code>\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚙️ <b>تنظیمات سیستم</b>\n"
        "━━━━━━━━━━━━\n"
        "فرمت: <code>/set کلید مقدار</code>\n\n"

        "<code>/set publish_start_hour 10</code>\n"
        "<code>/set publish_end_hour 23</code>\n"
        "<code>/set min_publish_interval 60</code>\n"
        "<code>/set max_publish_interval 120</code>\n"
        "<code>/set daily_meme_limit 3</code>\n"
        "<code>/set banner_price_12h 50000</code>\n"
        "<code>/set banner_price_24h 80000</code>\n"
        "<code>/set banner_price_72h 150000</code>\n"
        "<code>/set banner_reply_price 20000</code>\n"
        "<code>/set banner_pin_price 30000</code>\n"
        "<code>/set oneliner_ad_price 30000</code>\n"
        "<code>/set card_number 6037991234567890</code>\n"
        "<code>/set card_owner نام خود</code>\n"
        "<code>/set support_id @username</code>\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 <b>مدیریت سطوح</b>\n"
        "━━━━━━━━━━━━\n"
        "➕ افزودن سطح:\n"
        "<code>/addlevel مبتدی 5</code>\n"
        "<code>/addlevel افسانه‌ای 100</code>\n\n"

        "🗑 حذف سطح:\n"
        "<code>/dellevel 3</code> — شناسه سطح\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🏷 <b>کدهای تخفیف</b>\n"
        "━━━━━━━━━━━━\n"
        "➕ تخفیف درصدی:\n"
        "<code>/adddiscount SALE20 percent 20</code>\n\n"

        "➕ تخفیف مبلغ ثابت:\n"
        "<code>/adddiscount VIP fixed 10000</code>\n\n"

        "➕ با محدودیت تعداد:\n"
        "<code>/adddiscount CODE50 percent 50 10</code>\n"
        "<i>(آخرین عدد = حداکثر تعداد استفاده)</i>\n\n"

        "🗑 حذف کد:\n"
        "<code>/deldiscount SALE20</code>\n\n"

        "🔄 فعال/غیرفعال:\n"
        "<code>/togglediscount SALE20</code>\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 <b>آمار و گزارش</b>\n"
        "━━━━━━━━━━━━\n"
        "<code>/stats</code> — آمار کلی\n"
        "<code>/revenue</code> — گزارش درآمد\n"
        "<code>/logs 20</code> — ۲۰ لاگ اخیر\n"
        "<code>/userlogs 123456789</code> — لاگ کاربر\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🖼 <b>تنظیم عکس نمونه تک‌خطی</b>\n"
        "━━━━━━━━━━━━\n"
        "عکس را با کپشن زیر ارسال کنید:\n"
        "<code>/set_sample_image</code>"
    )

    await message.answer(text)


@router.message(Command("guide"))
async def cmd_guide(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await admin_guide(message, is_admin=True)