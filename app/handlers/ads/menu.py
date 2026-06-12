from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards.user_kb import ads_menu_kb

router = Router(name="ads_menu")


@router.message(F.text == "📢 تبلیغات")
async def ads_menu(message: Message, state: FSMContext, **kwargs) -> None:
    await state.clear()
    await message.answer(
        "📢 <b>منوی تبلیغات</b>\n\n"
        "نوع تبلیغ مورد نظر را انتخاب کنید:",
        reply_markup=ads_menu_kb(),
    )