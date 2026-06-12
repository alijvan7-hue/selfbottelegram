from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.core.config import config
from app.core.database import AsyncSessionFactory
from app.services.revenue_service import RevenueService
from app.services.statistics_service import StatisticsService
from app.utils.date_helper import to_jalali
from app.utils.text_helper import fa_number

router = Router(name="revenue")


def _is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


@router.callback_query(F.data == "admin_revenue")
async def show_revenue_callback(callback: CallbackQuery, **kwargs) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return

    async with AsyncSessionFactory() as session:
        svc = StatisticsService(session)
        revenue = await svc.get_revenue_breakdown()

    text = _build_revenue_text(revenue)
    await callback.message.edit_text(text, reply_markup=None)
    await callback.answer()


@router.message(F.text == "💰 درآمد")
async def revenue_btn(message: Message, is_admin: bool, **kwargs) -> None:
    if not is_admin:
        return
    await _send_revenue(message)


@router.message(Command("revenue"))
async def cmd_revenue(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await _send_revenue(message)


async def _send_revenue(message: Message) -> None:
    async with AsyncSessionFactory() as session:
        svc = StatisticsService(session)
        revenue = await svc.get_revenue_breakdown()
        jalali_month = await svc.get_jalali_month_revenue()

    text = _build_revenue_text(revenue, jalali_month)
    await message.answer(text)


def _build_revenue_text(revenue: dict, jalali_month: float = 0.0) -> str:
    return (
        f"💰 <b>گزارش درآمد</b>\n\n"
        f"📅 امروز: <b>{fa_number(revenue['today'])} تومان</b>\n"
        f"📆 هفته جاری: <b>{fa_number(revenue['week'])} تومان</b>\n"
        f"🗓 ماه میلادی: <b>{fa_number(revenue['month'])} تومان</b>\n"
        f"🗓 ماه شمسی: <b>{fa_number(jalali_month)} تومان</b>\n"
        f"📊 درآمد کل: <b>{fa_number(revenue['total'])} تومان</b>\n\n"
        f"📢 <b>درآمد بر اساس نوع:</b>\n"
        f"  • بنری: {fa_number(revenue['banner_total'])} تومان\n"
        f"  • تک‌خطی: {fa_number(revenue['oneliner_total'])} تومان"
    )