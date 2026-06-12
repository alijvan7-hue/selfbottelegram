from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.types import Message

from app.core.config import config
from app.core.database import AsyncSessionFactory
from app.keyboards.inline_kb import queue_item_kb
from app.services.queue_service import QueueService
from app.services.settings_service import SettingsService
from app.utils.date_helper import to_jalali
from app.utils.text_helper import fa_number

router = Router(name="queue_management")
logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


@router.message(F.text == "📋 صف انتشار")
async def show_queue_btn(message: Message, is_admin: bool, **kwargs) -> None:
    if not is_admin:
        return
    await _show_queue(message)


async def _show_queue(message: Message) -> None:
    async with AsyncSessionFactory() as session:
        queue_svc = QueueService(session)
        settings_svc = SettingsService(session)
        paused = await settings_svc.get_bool("queue_paused")
        waiting = await queue_svc.get_all_waiting()

    status_line = "⏸ متوقف" if paused else "▶️ فعال"

    if not waiting:
        await message.answer(
            f"📋 <b>صف انتشار — {status_line}</b>\n\n"
            "صف خالی است.\n\n"
            "💡 برای توقف: <code>/pause_queue</code>\n"
            "💡 برای ادامه: <code>/resume_queue</code>"
        )
        return

    await message.answer(
        f"📋 <b>صف انتشار — {status_line}</b>\n"
        f"تعداد: <b>{fa_number(len(waiting))}</b> آیتم\n\n"
        "💡 <code>/pause_queue</code> — توقف\n"
        "💡 <code>/resume_queue</code> — ادامه\n"
        "💡 <code>/publish_now ID</code> — انتشار فوری\n"
        "━━━━━━━━━━━━━━━"
    )

    for entry in waiting[:10]:
        await message.answer(
            f"🔢 میم <code>#{entry.meme_id}</code>\n"
            f"🕐 زمان: {to_jalali(entry.scheduled_time)}",
            reply_markup=queue_item_kb(entry.id, entry.meme_id),
        )


@router.message(F.text == "📢 تبلیغات پندینگ")
async def show_pending_ads(message: Message, is_admin: bool, **kwargs) -> None:
    if not is_admin:
        return

    async with AsyncSessionFactory() as session:
        from app.repositories.ad_repo import AdRepository
        repo = AdRepository(session)
        pending = await repo.get_pending()
        payment_pending = await repo.get_payment_pending()

    if not pending and not payment_pending:
        await message.answer(
            "📢 <b>تبلیغات در انتظار</b>\n\n"
            "هیچ تبلیغی در انتظار بررسی نیست. ✅"
        )
        return

    if pending:
        await message.answer(
            f"📢 <b>تبلیغات در انتظار تایید:</b> {len(pending)} عدد\n"
            "━━━━━━━━━━━━━━━"
        )
        for ad in pending[:5]:
            from app.keyboards.inline_kb import ad_review_kb
            from app.utils.text_helper import fa_number
            text = (
                f"📋 تبلیغ <code>#{ad.id}</code>\n"
                f"📌 نوع: {'بنری' if ad.ad_type == 'banner' else 'تک‌خطی'}\n"
                f"💰 مبلغ: {fa_number(ad.final_price)} تومان\n"
                f"📝 متن: {ad.text[:80]}..."
            )
            await message.answer(text, reply_markup=ad_review_kb(ad.id))

    if payment_pending:
        await message.answer(
            f"💳 <b>در انتظار تایید پرداخت:</b> {len(payment_pending)} عدد\n"
            "━━━━━━━━━━━━━━━"
        )
        for ad in payment_pending[:5]:
            from app.keyboards.inline_kb import payment_review_kb
            from app.utils.text_helper import fa_number
            text = (
                f"💳 تبلیغ <code>#{ad.id}</code>\n"
                f"💰 مبلغ: {fa_number(ad.final_price)} تومان\n"
                f"📝 متن: {ad.text[:80]}..."
            )
            await message.answer(text, reply_markup=payment_review_kb(ad.id))