from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from app.core.database import AsyncSessionFactory
from app.services.settings_service import SettingsService

router = Router(name="support")


@router.message(F.text == "📞 پشتیبانی")
async def support_handler(message: Message, **kwargs) -> None:
    async with AsyncSessionFactory() as session:
        svc = SettingsService(session)
        support_id = await svc.get("support_id") or "@support_username"

    await message.answer(
        f"📞 <b>پشتیبانی</b>\n\n"
        f"برای ارتباط با پشتیبانی به آیدی زیر پیام دهید:\n\n"
        f"👤 {support_id}"
    )