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


async def _build_leaderboard(users, title: str, monthly: bool = False) -> str:
    if not users:
        return f"🏆 <b>{title}</b>\n\nهنوز کسی در لیدربرد نیست!"

    async with AsyncSessionFactory() as session:
        svc = UserService(session)
        lines = [f"🏆 <b>{title}</b>\n{'━' * 20}\n"]

        for i, u in enumerate(users):
            medal = _MEDALS[i] if i < 3 else f"{i + 1}."
            name = u.full_name or u.username or str(u.telegram_id)
            tokens = u.monthly_tokens if monthly else u.tokens

            # دریافت سطح کاربر
            level = await svc.get_level(u)
            level_badge = f" [{level.name}]" if level else ""

            lines.append(
                f"{medal} <b>{name}</b>{level_badge}\n"
                f"   🪙 {fa_number(tokens)} توکن"
            )

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
    text = await _build_leaderboard(users, "لیدربرد کلی", monthly=False)
    await message.answer(text)


@router.message(F.text == "🏆 لیدربرد ماهانه")
async def monthly_leaderboard(message: Message, **kwargs) -> None:
    async with AsyncSessionFactory() as session:
        svc = UserService(session)
        users = await svc.get_top_monthly(10)
    text = await _build_leaderboard(users, "لیدربرد ماهانه", monthly=True)
    await message.answer(text)
