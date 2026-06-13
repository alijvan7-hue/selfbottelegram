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
        "✨ <i>همه‌چیز درباره مدیریت ربات</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"

        "🎛 <b>پنل ادمین</b>\n"
        "━━━━━━━━━━━━\n"
        "با دستور <code>/admin</code> یا دکمه «🔐 پنل ادمین» وارد پنل می‌شوید. دکمه‌های پنل:\n"
        "📋 صف انتشار — مشاهده و مدیریت نوبت انتشار\n"
        "📢 تبلیغات پندینگ — تبلیغات در انتظار تایید\n"
        "💰 درآمد · 📈 آمار — گزارش‌های مالی و عملکرد\n"
        "👥 کاربران · ⚙️ تنظیمات · 🏷 تخفیف‌ها · 🎯 سطوح\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👥 <b>مدیریت کاربران</b>\n"
        "━━━━━━━━━━━━\n"
        "🔍 <b>اطلاعات کاربر</b>\n"
        "<code>/user 123456789</code>\n\n"

        "🚫 <b>بن کاربر</b>\n"
        "<code>/ban 123456789 7d</code> — ۷ روز\n"
        "<code>/ban 123456789 30d</code> — ۳۰ روز\n"
        "<code>/ban 123456789 permanent</code> — دائمی\n\n"

        "✅ <b>رفع بن</b>\n"
        "<code>/unban 123456789</code>\n\n"

        "🪙 <b>مدیریت توکن</b>\n"
        "<code>/addtoken 123456789 10</code> — افزایش\n"
        "<code>/removetoken 123456789 5</code> — کاهش\n\n"

        "📊 <b>محدودیت ارسال میم</b>\n"
        "<code>/setlimit 123456789 5</code> — ۵ میم در روز\n"
        "<code>/setlimit 123456789 unlimited</code> — بی‌نهایت\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 <b>مدیریت صف انتشار</b>\n"
        "━━━━━━━━━━━━\n"
        "🚀 <b>انتشار فوری</b>\n"
        "<code>/publish_now 42</code>\n\n"

        "🔁 <b>بازچینی صف</b>\n"
        "<code>/reorder_queue</code>\n\n"

        "⏸ <b>توقف / ادامه صف</b>\n"
        "<code>/pause_queue</code>\n"
        "<code>/resume_queue</code>\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔒 <b>قفل ربات</b>\n"
        "━━━━━━━━━━━━\n"
        "<code>/lock</code> — قفل کردن\n"
        "<code>/unlock</code> — باز کردن\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚙️ <b>تنظیمات سیستم</b>\n"
        "━━━━━━━━━━━━\n"
        "فرمت: <code>/set کلید مقدار</code>\n\n"

        "⏰ <u>زمان‌بندی انتشار</u>\n"
        "<code>/set publish_start_hour 10</code>\n"
        "<code>/set publish_end_hour 23</code>\n"
        "<code>/set min_publish_interval 60</code>\n"
        "<code>/set max_publish_interval 120</code>\n"
        "<code>/set daily_meme_limit 3</code>\n\n"

        "📢 <u>تعرفه تبلیغات بنری</u>\n"
        "<code>/set banner_price_12h 50000</code>\n"
        "<code>/set banner_price_24h 80000</code>\n"
        "<code>/set banner_price_72h 150000</code>\n"
        "<code>/set banner_reply_price 20000</code> — هزینه ریپلای خودکار\n"
        "<code>/set banner_pin_price 30000</code> — هزینه پین پیام\n\n"

        "📝 <u>تعرفه تبلیغات تک‌خطی</u>\n"
        "<code>/set oneliner_ad_price 30000</code> — قیمت پایه هر ۷ روز\n\n"

        "💳 <u>اطلاعات پرداخت و پشتیبانی</u>\n"
        "<code>/set card_number 6037991234567890</code>\n"
        "<code>/set card_owner نام خود</code>\n"
        "<code>/set support_id @username</code>\n\n"

        "💬 <u>متن راهنمای کاربران</u>\n"
        "<code>/set help_text متن دلخواه</code>\n"
        "این متن با دستور <code>/help</code> برای کاربران نمایش داده می‌شود.\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 <b>مدیریت سطوح</b>\n"
        "━━━━━━━━━━━━\n"
        "➕ <b>افزودن سطح</b>\n"
        "<code>/addlevel مبتدی 5</code>\n"
        "<code>/addlevel افسانه‌ای 100</code>\n\n"

        "🗑 <b>حذف سطح</b>\n"
        "<code>/dellevel 3</code> — بر اساس شناسه سطح\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🏷 <b>کدهای تخفیف</b>\n"
        "━━━━━━━━━━━━\n"
        "➕ <b>تخفیف درصدی</b>\n"
        "<code>/adddiscount SALE20 percent 20</code>\n\n"

        "➕ <b>تخفیف مبلغ ثابت</b>\n"
        "<code>/adddiscount VIP fixed 10000</code>\n\n"

        "➕ <b>با محدودیت تعداد استفاده</b>\n"
        "<code>/adddiscount CODE50 percent 50 10</code>\n"
        "<i>(عدد آخر = حداکثر تعداد استفاده)</i>\n\n"

        "🗑 <b>حذف کد</b>\n"
        "<code>/deldiscount SALE20</code>\n\n"

        "🔄 <b>فعال / غیرفعال کردن</b>\n"
        "<code>/togglediscount SALE20</code>\n\n"

        "💡 تخفیف روی <b>قیمت نهایی</b> تبلیغ (بنر + ریپلای + پین) اعمال می‌شود.\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 <b>آمار و گزارش</b>\n"
        "━━━━━━━━━━━━\n"
        "<code>/stats</code> — آمار کلی ربات\n"
        "<code>/revenue</code> — گزارش درآمد\n"
        "<code>/logs 20</code> — ۲۰ لاگ اخیر\n"
        "<code>/userlogs 123456789</code> — لاگ مخصوص یک کاربر\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🖼 <b>تبلیغات تک‌خطی — عکس و توضیحات نمونه</b>\n"
        "━━━━━━━━━━━━\n"
        "📸 عکس را با کپشن زیر ارسال کنید:\n"
        "<code>/set_sample_image</code>\n\n"
        "📝 توضیحات نمونه:\n"
        "<code>/set oneliner_description متن دلخواه</code>\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔁 برای مشاهده دوباره این راهنما، هر زمان <code>/guide</code> را بزنید.\n\n"
        "ℹ️ کاربران از طریق «📊 وضعیت تبلیغات من» (داخل منوی تبلیغات) "
        "می‌توانند وضعیت و زمان دقیق انتشار/پایان تبلیغ خود را ببینند، "
        "و هنگام انتشار و پایان تبلیغ به‌صورت خودکار پیام دریافت می‌کنند."
    )

    await message.answer(text)


@router.message(Command("guide"))
async def cmd_guide(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await admin_guide(message, is_admin=True)
