from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.core.config import config
from app.core.database import AsyncSessionFactory
from app.services.statistics_service import StatisticsService
from app.utils.text_helper import fa_number

router = Router(name="statistics")


def _is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


@router.message(Command("stats"))
async def cmd_stats(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await _send_global_stats(message)


@router.message(F.text == "📈 آمار کلی")
async def stats_btn(message: Message, is_admin: bool, **kwargs) -> None:
    if not is_admin:
        return
    await _send_global_stats(message)


async def _send_global_stats(message: Message) -> None:
    async with AsyncSessionFactory() as session:
        svc = StatisticsService(session)
        stats = await svc.get_global_stats()
        revenue = await svc.get_revenue_breakdown()
        approval_rate = await svc.get_meme_approval_rate()
        new_users = await svc.get_new_users_today()

    text = (
        f"📈 <b>آمار کلی سیستم</b>\n\n"
        f"👥 <b>کاربران</b>\n"
        f"  • کل: {fa_number(stats['total_users'])}\n"
        f"  • جدید امروز: {fa_number(new_users)}\n\n"
        f"🎭 <b>میم‌ها</b>\n"
        f"  • کل ثبت‌شده: {fa_number(stats['total_memes'])}\n"
        f"  • تایید شده: {fa_number(stats['approved_memes'])}\n"
        f"  • منتشر شده: {fa_number(stats['published_memes'])}\n"
        f"  • نرخ تایید: {approval_rate}٪\n\n"
        f"📢 <b>تبلیغات</b>\n"
        f"  • کل: {fa_number(stats['total_ads'])}\n"
        f"  • منتشر شده: {fa_number(stats['published_ads'])}\n\n"
        f"💰 <b>درآمد</b>\n"
        f"  • امروز: {fa_number(revenue['today'])} تومان\n"
        f"  • هفته: {fa_number(revenue['week'])} تومان\n"
        f"  • ماه: {fa_number(revenue['month'])} تومان\n"
        f"  • کل: {fa_number(revenue['total'])} تومان\n"
        f"  • بنری: {fa_number(revenue['banner_total'])} تومان\n"
        f"  • تک‌خطی: {fa_number(revenue['oneliner_total'])} تومان"
    )
    await message.answer(text)


@router.callback_query(F.data == "admin_stats")
async def stats_callback(callback: CallbackQuery, **kwargs) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return

    async with AsyncSessionFactory() as session:
        svc = StatisticsService(session)
        stats = await svc.get_global_stats()
        revenue = await svc.get_revenue_breakdown()
        approval_rate = await svc.get_meme_approval_rate()
        new_users = await svc.get_new_users_today()

    text = (
        f"📈 <b>آمار کلی سیستم</b>\n\n"
        f"👥 کاربران: {fa_number(stats['total_users'])} (امروز: +{fa_number(new_users)})\n"
        f"🎭 میم کل: {fa_number(stats['total_memes'])} | منتشر: {fa_number(stats['published_memes'])}\n"
        f"✅ نرخ تایید: {approval_rate}٪\n"
        f"📢 تبلیغات منتشر: {fa_number(stats['published_ads'])}\n\n"
        f"💰 درآمد امروز: {fa_number(revenue['today'])} تومان\n"
        f"💰 درآمد کل: {fa_number(revenue['total'])} تومان"
    )

    await callback.message.edit_text(text, reply_markup=None)
    await callback.answer()