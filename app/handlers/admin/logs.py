from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.core.config import config
from app.core.database import AsyncSessionFactory
from app.repositories.log_repo import LogRepository
from app.utils.date_helper import to_jalali

router = Router(name="logs")


def _is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


@router.message(Command("logs"))
async def cmd_logs(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()
    limit = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10

    async with AsyncSessionFactory() as session:
        repo = LogRepository(session)
        logs = await repo.get_recent(min(limit, 30))

    if not logs:
        await message.answer("هیچ لاگی ثبت نشده.")
        return

    lines = [f"📋 <b>آخرین {len(logs)} رویداد</b>\n"]
    for log in logs:
        date_str = to_jalali(log.created_at)
        lines.append(
            f"• <code>{log.event_type}</code>\n"
            f"  {log.description or '—'}\n"
            f"  🕐 {date_str}"
        )

    await message.answer("\n".join(lines))


@router.message(Command("userlogs"))
async def cmd_user_logs(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
        await message.answer("استفاده: /userlogs <telegram_id>")
        return

    user_id = int(parts[1])

    async with AsyncSessionFactory() as session:
        repo = LogRepository(session)
        logs = await repo.get_by_user(user_id, limit=15)

    if not logs:
        await message.answer(f"هیچ لاگی برای کاربر {user_id} یافت نشد.")
        return

    lines = [f"📋 <b>لاگ‌های کاربر {user_id}</b>\n"]
    for log in logs:
        date_str = to_jalali(log.created_at)
        lines.append(
            f"• <code>{log.event_type}</code> — {date_str}\n"
            f"  {log.description or '—'}"
        )

    await message.answer("\n".join(lines))