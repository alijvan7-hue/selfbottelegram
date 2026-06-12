from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message

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

    status = "⏸ متوقف" if paused else "▶️ فعال"

    header = (
        f"📋 <b>صف انتشار — {status}</b>\n"
        f"تعداد: <b>{fa_number(len(waiting))}</b> آیتم\n\n"
        "💡 دستورات:\n"
        "<code>/pause_queue</code> — توقف\n"
        "<code>/resume_queue</code> — ادامه\n"
        "<code>/publish_now ID</code> — انتشار فوری\n"
        "<code>/reorder_queue</code> — بازچینی صف"
    )

    if not waiting:
        await message.answer(header + "\n\n📭 صف خالی است.")
        return

    await message.answer(header)

    for entry in waiting[:15]:
        await message.answer(
            f"🔢 میم <code>#{entry.meme_id}</code>\n"
            f"🕐 زمان: {to_jalali(entry.scheduled_time)}",
            reply_markup=queue_item_kb(entry.id, entry.meme_id),
        )


# ── بازچینی دستی صف ──────────────────────────────────────────────────────────
from aiogram.filters import Command


@router.message(Command("reorder_queue"))
async def cmd_reorder_queue(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    async with AsyncSessionFactory() as session:
        queue_svc = QueueService(session)
        settings_svc = SettingsService(session)
        count = await queue_svc.count_waiting()

        if count == 0:
            await message.answer("📭 صف خالی است.")
            return

        await queue_svc.reorder_queue(settings_svc)
        await session.commit()

    await message.answer(
        f"✅ صف بازچینی شد!\n"
        f"{fa_number(count)} آیتم مجدداً زمان‌بندی شدند."
    )


# ── انتشار فوری از callback ───────────────────────────────────────────────────
@router.callback_query(F.data.startswith("q_publish_now:"))
async def queue_publish_now(callback: CallbackQuery, bot: Bot, **kwargs) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return

    meme_id = int(callback.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        from app.services.meme_service import MemeService
        queue_svc = QueueService(session)
        meme_svc = MemeService(session)
        settings_svc = SettingsService(session)

        meme = await meme_svc.get_by_id(meme_id)
        if not meme or meme.is_published:
            await callback.answer("میم قابل انتشار نیست.", show_alert=True)
            return

        result = await queue_svc.publish_immediately(meme, bot)
        # بازچینی خودکار بعد از انتشار
        await queue_svc.reorder_queue(settings_svc)
        await session.commit()

    if result:
        await callback.answer("✅ منتشر شد!")
        try:
            await callback.message.edit_text(
                (callback.message.text or "") + "\n\n✅ منتشر شد",
                reply_markup=None,
            )
        except Exception:
            pass
    else:
        await callback.answer("❌ انتشار ناموفق.", show_alert=True)


# ── حذف از صف + بازچینی خودکار ───────────────────────────────────────────────
@router.callback_query(F.data.startswith("q_remove:"))
async def queue_remove(callback: CallbackQuery, **kwargs) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return

    queue_id = int(callback.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        queue_svc = QueueService(session)
        settings_svc = SettingsService(session)
        # حذف + بازچینی خودکار
        removed = await queue_svc.cancel_queue_entry(queue_id, settings_svc)
        await session.commit()

    if removed:
        await callback.answer("🗑 حذف شد و صف بازچینی شد.")
        try:
            await callback.message.edit_text(
                (callback.message.text or "") + "\n\n🗑 حذف + بازچینی شد",
                reply_markup=None,
            )
        except Exception:
            pass
    else:
        await callback.answer("آیتم یافت نشد.", show_alert=True)


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
        await message.answer("📢 <b>تبلیغات پندینگ</b>\n\nهیچ تبلیغی در انتظار نیست. ✅")
        return

    if pending:
        await message.answer(
            f"📢 <b>در انتظار تایید:</b> {len(pending)} عدد\n━━━━━━━━━━━━━━━"
        )
        for ad in pending[:5]:
            from app.keyboards.inline_kb import ad_review_kb
            await message.answer(
                f"📋 <code>#{ad.id}</code> — {'بنری' if ad.ad_type == 'banner' else 'تک‌خطی'}\n"
                f"💰 {fa_number(ad.final_price)} تومان\n"
                f"📝 {ad.text[:60]}...",
                reply_markup=ad_review_kb(ad.id),
            )

    if payment_pending:
        await message.answer(
            f"💳 <b>در انتظار تایید پرداخت:</b> {len(payment_pending)} عدد\n━━━━━━━━━━━━━━━"
        )
        for ad in payment_pending[:5]:
            from app.keyboards.inline_kb import payment_review_kb
            await message.answer(
                f"💳 <code>#{ad.id}</code> — {'بنری' if ad.ad_type == 'banner' else 'تک‌خطی'}\n"
                f"💰 {fa_number(ad.final_price)} تومان",
                reply_markup=payment_review_kb(ad.id),
            )
