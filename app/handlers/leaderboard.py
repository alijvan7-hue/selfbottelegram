from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.core.database import AsyncSessionFactory
from app.keyboards.user_kb import leaderboard_menu_kb
from app.services.user_service import UserService
from app.utils.text_helper import fa_number

router = Router(name="leaderboard")

_MEDALS = ["🥇", "🥈", "🥉"]


def _truncate_name(name: str, max_len: int = 30) -> str:
    """اسم را حداکثر تا ۳۰ کاراکتر نشان بده"""
    if len(name) <= max_len:
        return name
    return name[:max_len] + "..."


async def _build_leaderboard_text(users, title: str, monthly: bool = False) -> str:
    if not users:
        return f"🏆 <b>{title}</b>\n\nهنوز کسی در لیدربرد نیست!"

    lines = [f"🏆 <b>{title}</b>\n{'━' * 20}\n"]

    async with AsyncSessionFactory() as session:
        svc = UserService(session)
        for i, u in enumerate(users):
            medal = _MEDALS[i] if i < 3 else f"{i + 1}."
            raw_name = u.full_name or u.username or str(u.telegram_id)
            name = _truncate_name(raw_name, 30)
            tokens = u.monthly_tokens if monthly else u.tokens
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
    await message.answer(
        "لیدربرد را انتخاب کنید:",
        reply_markup=leaderboard_menu_kb(),
    )


@router.message(F.text == "🏆 لیدربرد کلی")
async def overall_leaderboard(message: Message, **kwargs) -> None:
    async with AsyncSessionFactory() as session:
        svc = UserService(session)
        users = await svc.get_top_overall(10)
    text = await _build_leaderboard_text(users, "لیدربرد کلی", monthly=False)
    await message.answer(text)


@router.message(F.text == "🏆 لیدربرد ماهانه")
async def monthly_leaderboard(message: Message, **kwargs) -> None:
    async with AsyncSessionFactory() as session:
        svc = UserService(session)
        users = await svc.get_top_monthly(10)
    text = await _build_leaderboard_text(users, "لیدربرد ماهانه", monthly=True)
    await message.answer(text)
