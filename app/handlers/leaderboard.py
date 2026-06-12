from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.core.database import AsyncSessionFactory
from app.keyboards.user_kb import leaderboard_menu_kb, main_menu_kb
from app.services.user_service import UserService
from app.utils.text_helper import fa_number

router = Router(name="leaderboard")

_MEDALS = ["🥇", "🥈", "🥉"]


def _build_leaderboard(users, title: str) -> str:
    if not users:
        return f"🏆 <b>{title}</b>\n\nهنوز کسی در لیدربرد نیست!"

    lines = [f"🏆 <b>{title}</b>\n"]
    for i, u in enumerate(users):
        medal = _MEDALS[i] if i < 3 else f"{i + 1}."
        name = u.full_name or u.username or str(u.telegram_id)
        tokens = u.monthly_tokens if "ماهانه" in title else u.tokens
        lines.append(f"{medal} <b>{name}</b> — {fa_number(tokens)} توکن")
    return "\n".join(lines)


@router.message(F.text == "🏆 لیدربرد")
async def leaderboard_menu(message: Message, state: FSMContext, **kwargs) -> None:
    await state.clear()
    await message.answer("لیدربرد را انتخاب کنید:", reply_markup=leaderboard_menu_kb())


@router.message(F.text == "🏆 لیدربرد کلی")
async def overall_leaderboard(message: Message, **kwargs) -> None:
    async with AsyncSessionFactory() as session:
        svc = UserService(session)
        users = await svc.get_top_overall(10)
    await message.answer(_build_leaderboard(users, "لیدربرد کلی"))


@router.message(F.text == "🏆 لیدربرد ماهانه")
async def monthly_leaderboard(message: Message, **kwargs) -> None:
    async with AsyncSessionFactory() as session:
        svc = UserService(session)
        users = await svc.get_top_monthly(10)
    await message.answer(_build_leaderboard(users, "لیدربرد ماهانه"))