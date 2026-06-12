from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.core.config import config
from app.core.database import AsyncSessionFactory
from app.keyboards.admin_kb import admin_main_kb
from app.keyboards.user_kb import main_menu_kb
from app.services.queue_service import QueueService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService
from app.utils.text_helper import fa_number

router = Router(name="admin_panel")
logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


@router.message(Command("admin"))
async def cmd_admin(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        await message.answer("❌ دسترسی ندارید.")
        return
    await _show_admin_panel(message)


@router.message(F.text == "🔐 پنل ادمین")
async def admin_panel_btn(message: Message, is_admin: bool, **kwargs) -> None:
    if not is_admin:
        return
    await _show_admin_panel(message)


async def _show_admin_panel(message: Message) -> None:
    async with AsyncSessionFactory() as session:
        settings_svc = SettingsService(session)
        queue_svc = QueueService(session)
        user_svc = UserService(session)

        paused = await settings_svc.get_bool("queue_paused")
        locked = await settings_svc.get_bool("bot_locked")
        queue_count = await queue_svc.count_waiting()
        user_count = await user_svc.count_all()

    queue_status = "⏸ متوقف" if paused else "▶️ فعال"
    lock_status = "🔒 قفل" if locked else "🔓 باز"

    await message.answer(
        f"🔐 <b>پنل ادمین</b>\n\n"
        f"📋 صف انتشار: <b>{queue_status}</b> ({fa_number(queue_count)} آیتم)\n"
        f"🔒 وضعیت ربات: <b>{lock_status}</b>\n"
        f"👥 کاربران: <b>{fa_number(user_count)}</b>\n\n"
        "از منوی پایین گزینه مورد نظر را انتخاب کنید:",
        reply_markup=admin_main_kb(),
    )


@router.message(F.text == "🔙 منوی اصلی")
async def back_to_main(message: Message, is_admin: bool, **kwargs) -> None:
    await message.answer("منوی اصلی:", reply_markup=main_menu_kb(is_admin=is_admin))