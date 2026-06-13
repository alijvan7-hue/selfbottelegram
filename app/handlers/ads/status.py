from __future__ import annotations

from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.types import Message

from app.core.database import AsyncSessionFactory
from app.repositories.ad_repo import AdRepository
from app.utils.date_helper import time_remaining_fa, to_jalali_full
from app.utils.text_helper import fa_number, truncate

router = Router(name="ads_status")

_STATUS_LABELS = {
    "pending": "⏳ <b>در انتظار تایید محتوا</b> توسط ادمین",
    "rejected": "❌ <b>رد شده</b>",
    "payment_pending": "💳 <b>در انتظار تایید پرداخت</b>",
}


@router.message(F.text == "📊 وضعیت تبلیغات من")
async def my_ads_status(message: Message, user, **kwargs) -> None:
    async with AsyncSessionFactory() as session:
        repo = AdRepository(session)
        ads = await repo.get_by_user(user.id)

    if not ads:
        await message.answer("📭 شما تا کنون هیچ تبلیغی ثبت نکرده‌اید.")
        return

    now = datetime.now(timezone.utc)

    for ad in ads[:10]:
        ad_type_label = "بنری" if ad.ad_type == "banner" else "تک‌خطی"
        lines = [
            f"📋 <b>تبلیغ #{ad.id}</b> — {ad_type_label}",
            f"📝 {truncate(ad.text, 60)}",
            "━━━━━━━━━━━━━━━",
        ]

        if ad.status in _STATUS_LABELS:
            lines.append(_STATUS_LABELS[ad.status])

        elif ad.status == "payment_approved":
            if ad.publish_at:
                lines.append(f"📅 <b>زمان انتشار:</b>\n{to_jalali_full(ad.publish_at)}")
            else:
                lines.append("🕐 <b>در صف انتشار</b> — به‌زودی زمان‌بندی می‌شود")

        elif ad.status == "published":
            lines.append("✅ <b>منتشر شده</b>")
            if ad.published_at:
                lines.append(f"📅 زمان انتشار: {to_jalali_full(ad.published_at)}")
            if ad.expires_at:
                if ad.expires_at > now:
                    lines.append(
                        f"⏳ <b>{time_remaining_fa(ad.expires_at)}</b> تا پایان نمایش"
                    )
                    lines.append(f"🔚 پایان نمایش: {to_jalali_full(ad.expires_at)}")
                else:
                    lines.append("🔚 به‌زودی از کانال حذف می‌شود")

        elif ad.status == "expired":
            lines.append("🔚 <b>نمایش این تبلیغ به پایان رسیده</b> و از کانال حذف شده است.")

        else:
            lines.append(f"وضعیت: {ad.status}")

        lines.append(f"💰 مبلغ: {fa_number(ad.final_price)} تومان")

        await message.answer("\n".join(lines))
