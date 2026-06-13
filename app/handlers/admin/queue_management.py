from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.core.config import config
from app.core.database import AsyncSessionFactory
from app.services.queue_service import QueueService
from app.services.settings_service import SettingsService
from app.states.admin_states import AdminQueueStates
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
        from app.repositories.ad_repo import AdRepository
        from app.repositories.meme_repo import MemeRepository

        queue_svc = QueueService(session)
        settings_svc = SettingsService(session)
        ad_repo = AdRepository(session)
        meme_repo = MemeRepository(session)

        paused = await settings_svc.get_bool("queue_paused")
        waiting = await queue_svc.get_all_waiting()
        scheduled_ads = await ad_repo.get_scheduled()

        items: list[tuple] = []
        for entry in waiting:
            meme = await meme_repo.get_by_id(entry.meme_id)
            label = "🌟 <b>شاهکار</b>" if meme and meme.is_masterpiece else "🎭 میم"
            items.append(
                (
                    entry.scheduled_time,
                    f"🔢 <code>#{entry.meme_id}</code> — {label} — 🕐 {to_jalali(entry.scheduled_time)}",
                )
            )

        for ad in scheduled_ads:
            items.append(
                (
                    ad.publish_at,
                    f"📢 <code>#{ad.id}</code> — <b>تبلیغات</b> — 🕐 {to_jalali(ad.publish_at)}",
                )
            )

    items.sort(key=lambda x: x[0])

    status = "⏸ متوقف" if paused else "▶️ فعال"
    header = (
        f"📋 <b>صف انتشار — {status}</b>\n"
        f"تعداد: <b>{fa_number(len(waiting))}</b> میم"
        + (f" + <b>{fa_number(len(scheduled_ads))}</b> تبلیغ" if scheduled_ads else "")
        + "\n\n"
        "💡 دستورات:\n"
        "<code>/pause_queue</code> — توقف\n"
        "<code>/resume_queue</code> — ادامه\n"
        "<code>/publish_now ID</code> — انتشار فوری\n"
        "<code>/reorder_queue</code> — بازچینی صف\n"
        "━━━━━━━━━━━━━━━\n"
    )

    if not items:
        await message.answer(header + "\n📭 صف خالی است.")
        return

    body = "\n".join(line for _, line in items[:25])
    text = header + body

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑 حذف", callback_data="queue_remove_prompt"),
        InlineKeyboardButton(text="🚀 انتشار فوری", callback_data="queue_publish_prompt"),
    )
    await message.answer(text, reply_markup=builder.as_markup())


# ── حذف از صف با آیدی ────────────────────────────────────────────────────────
@router.callback_query(F.data == "queue_remove_prompt")
async def queue_remove_prompt(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return
    await state.set_state(AdminQueueStates.waiting_remove_id)
    await callback.message.answer("🗑 آیدی میم مورد نظر برای حذف از صف را ارسال کنید:")
    await callback.answer()


@router.message(AdminQueueStates.waiting_remove_id, F.text)
async def queue_remove_by_id(message: Message, state: FSMContext, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    raw = (message.text or "").strip().lstrip("#")
    if not raw.isdigit():
        await message.answer("⚠️ لطفاً فقط عدد آیدی میم را ارسال کنید.")
        return

    meme_id = int(raw)
    async with AsyncSessionFactory() as session:
        queue_svc = QueueService(session)
        settings_svc = SettingsService(session)

        entry = await queue_svc.get_by_meme_id(meme_id)
        if not entry:
            await message.answer(f"❌ میم <code>#{meme_id}</code> در صف یافت نشد.")
            await state.clear()
            return

        await queue_svc.cancel_queue_entry(entry.id, settings_svc)
        await session.commit()

    await state.clear()
    await message.answer(f"🗑 میم <code>#{meme_id}</code> از صف حذف شد و صف بازچینی شد.")
    await _show_queue(message)


# ── انتشار فوری با آیدی ──────────────────────────────────────────────────────
@router.callback_query(F.data == "queue_publish_prompt")
async def queue_publish_prompt(callback: CallbackQuery, state: FSMContext, **kwargs) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return
    await state.set_state(AdminQueueStates.waiting_publish_id)
    await callback.message.answer("🚀 آیدی میم مورد نظر برای انتشار فوری را ارسال کنید:")
    await callback.answer()


@router.message(AdminQueueStates.waiting_publish_id, F.text)
async def queue_publish_by_id(message: Message, state: FSMContext, bot: Bot, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    raw = (message.text or "").strip().lstrip("#")
    if not raw.isdigit():
        await message.answer("⚠️ لطفاً فقط عدد آیدی میم را ارسال کنید.")
        return

    meme_id = int(raw)
    async with AsyncSessionFactory() as session:
        from app.services.meme_service import MemeService

        meme_svc = MemeService(session)
        queue_svc = QueueService(session)
        settings_svc = SettingsService(session)

        meme = await meme_svc.get_by_id(meme_id)
        if not meme or meme.is_published:
            await message.answer(f"❌ میم <code>#{meme_id}</code> قابل انتشار نیست.")
            await state.clear()
            return

        result = await queue_svc.publish_immediately(meme, bot)
        await queue_svc.reorder_queue(settings_svc)
        await session.commit()

    await state.clear()
    if result:
        await message.answer(f"✅ میم <code>#{meme_id}</code> منتشر شد.")
        await _show_queue(message)
    else:
        await message.answer("❌ انتشار ناموفق.")


# ── بازچینی دستی صف ──────────────────────────────────────────────────────────
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
