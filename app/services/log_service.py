from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import config
from app.models.log import SystemLog
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class LogRepository(BaseRepository[SystemLog]):
    model = SystemLog


# ── Event type constants ──────────────────────────────────────────────────────
class LogEvent:
    MEME_APPROVED = "meme_approved"
    MEME_REJECTED = "meme_rejected"
    MEME_PUBLISHED = "meme_published"
    AD_SUBMITTED = "ad_submitted"
    AD_APPROVED = "ad_approved"
    AD_REJECTED = "ad_rejected"
    AD_PUBLISHED = "ad_published"
    AD_EXPIRED = "ad_expired"
    PAYMENT_RECEIPT = "payment_receipt_submitted"
    PAYMENT_APPROVED = "payment_approved"
    PAYMENT_REJECTED = "payment_rejected"
    USER_BANNED = "user_banned"
    USER_UNBANNED = "user_unbanned"
    SETTINGS_CHANGED = "settings_changed"
    USER_REGISTERED = "user_registered"
    TOKEN_ADDED = "token_added"
    TOKEN_REMOVED = "token_removed"
    LIMIT_CHANGED = "limit_changed"
    QUEUE_PAUSED = "queue_paused"
    QUEUE_RESUMED = "queue_resumed"
    BOT_LOCKED = "bot_locked"
    BOT_UNLOCKED = "bot_unlocked"
    MONTHLY_RESET = "monthly_reset"
    LEVEL_ADDED = "level_added"
    LEVEL_DELETED = "level_deleted"
    DISCOUNT_ADDED = "discount_added"
    DISCOUNT_DELETED = "discount_deleted"


# ── Emoji map for log channel messages ───────────────────────────────────────
_EVENT_EMOJI: Dict[str, str] = {
    LogEvent.MEME_APPROVED: "✅",
    LogEvent.MEME_REJECTED: "❌",
    LogEvent.MEME_PUBLISHED: "📤",
    LogEvent.AD_SUBMITTED: "📝",
    LogEvent.AD_APPROVED: "✅",
    LogEvent.AD_REJECTED: "❌",
    LogEvent.AD_PUBLISHED: "📢",
    LogEvent.AD_EXPIRED: "🗑",
    LogEvent.PAYMENT_RECEIPT: "🧾",
    LogEvent.PAYMENT_APPROVED: "💰",
    LogEvent.PAYMENT_REJECTED: "❌",
    LogEvent.USER_BANNED: "🚫",
    LogEvent.USER_UNBANNED: "✅",
    LogEvent.SETTINGS_CHANGED: "⚙️",
    LogEvent.USER_REGISTERED: "👤",
    LogEvent.TOKEN_ADDED: "🪙",
    LogEvent.TOKEN_REMOVED: "🪙",
    LogEvent.LIMIT_CHANGED: "📊",
    LogEvent.QUEUE_PAUSED: "⏸",
    LogEvent.QUEUE_RESUMED: "▶️",
    LogEvent.BOT_LOCKED: "🔒",
    LogEvent.BOT_UNLOCKED: "🔓",
    LogEvent.MONTHLY_RESET: "🔄",
    LogEvent.LEVEL_ADDED: "🎯",
    LogEvent.LEVEL_DELETED: "🗑",
    LogEvent.DISCOUNT_ADDED: "🏷",
    LogEvent.DISCOUNT_DELETED: "🗑",
}


class LogService:
    def __init__(self, session: AsyncSession, bot: Optional[Bot] = None) -> None:
        self._repo = LogRepository(session)
        self._bot = bot

    async def log(
        self,
        event_type: str,
        description: str,
        user_id: Optional[int] = None,
        admin_id: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
        send_to_channel: bool = True,
    ) -> None:
        extra_str = json.dumps(extra, ensure_ascii=False) if extra else None

        try:
            await self._repo.create(
                event_type=event_type,
                description=description,
                user_id=user_id,
                admin_id=admin_id,
                extra_data=extra_str,
            )
        except Exception as exc:
            logger.error("Failed to write log to DB: %s", exc)

        if send_to_channel and self._bot and config.log_channel_id:
            try:
                text = self._build_log_text(
                    event_type, description, user_id, admin_id, extra
                )
                await self._bot.send_message(
                    config.log_channel_id,
                    text,
                    disable_web_page_preview=True,
                )
            except Exception as exc:
                logger.warning("Failed to send log to channel: %s", exc)

    def _build_log_text(
        self,
        event_type: str,
        description: str,
        user_id: Optional[int],
        admin_id: Optional[int],
        extra: Optional[Dict[str, Any]],
    ) -> str:
        emoji = _EVENT_EMOJI.get(event_type, "📋")
        lines = [
            f"{emoji} <b>{event_type.replace('_', ' ').title()}</b>",
            f"📝 {description}",
        ]
        if user_id:
            lines.append(f"👤 کاربر: <code>{user_id}</code>")
        if admin_id:
            lines.append(f"🔑 ادمین: <code>{admin_id}</code>")
        if extra:
            for k, v in extra.items():
                lines.append(f"  ▪️ {k}: <code>{v}</code>")
        return "\n".join(lines)

    # ── Convenience methods ───────────────────────────────────────────────
    async def meme_approved(
        self, meme_id: int, user_id: int, admin_id: int
    ) -> None:
        await self.log(
            LogEvent.MEME_APPROVED,
            f"میم #{meme_id} تایید شد.",
            user_id=user_id,
            admin_id=admin_id,
            extra={"meme_id": meme_id},
        )

    async def meme_rejected(
        self, meme_id: int, user_id: int, admin_id: int
    ) -> None:
        await self.log(
            LogEvent.MEME_REJECTED,
            f"میم #{meme_id} رد شد.",
            user_id=user_id,
            admin_id=admin_id,
            extra={"meme_id": meme_id},
        )

    async def meme_published(self, meme_id: int, user_id: int) -> None:
        await self.log(
            LogEvent.MEME_PUBLISHED,
            f"میم #{meme_id} منتشر شد.",
            user_id=user_id,
            extra={"meme_id": meme_id},
        )

    async def ad_approved(
        self, ad_id: int, user_id: int, admin_id: int, ad_type: str
    ) -> None:
        await self.log(
            LogEvent.AD_APPROVED,
            f"تبلیغ #{ad_id} ({ad_type}) تایید شد.",
            user_id=user_id,
            admin_id=admin_id,
            extra={"ad_id": ad_id, "type": ad_type},
        )

    async def ad_rejected(
        self, ad_id: int, user_id: int, admin_id: int
    ) -> None:
        await self.log(
            LogEvent.AD_REJECTED,
            f"تبلیغ #{ad_id} رد شد.",
            user_id=user_id,
            admin_id=admin_id,
            extra={"ad_id": ad_id},
        )

    async def payment_approved(
        self, ad_id: int, user_id: int, admin_id: int, amount: float
    ) -> None:
        await self.log(
            LogEvent.PAYMENT_APPROVED,
            f"پرداخت تبلیغ #{ad_id} تایید شد. مبلغ: {amount:,.0f} تومان",
            user_id=user_id,
            admin_id=admin_id,
            extra={"ad_id": ad_id, "amount": amount},
        )

    async def payment_rejected(
        self, ad_id: int, user_id: int, admin_id: int
    ) -> None:
        await self.log(
            LogEvent.PAYMENT_REJECTED,
            f"پرداخت تبلیغ #{ad_id} رد شد.",
            user_id=user_id,
            admin_id=admin_id,
            extra={"ad_id": ad_id},
        )

    async def user_banned(
        self, target_id: int, ban_type: str, admin_id: int
    ) -> None:
        await self.log(
            LogEvent.USER_BANNED,
            f"کاربر {target_id} بن شد ({ban_type}).",
            user_id=target_id,
            admin_id=admin_id,
            extra={"ban_type": ban_type},
        )

    async def user_unbanned(self, target_id: int, admin_id: int) -> None:
        await self.log(
            LogEvent.USER_UNBANNED,
            f"بن کاربر {target_id} برداشته شد.",
            user_id=target_id,
            admin_id=admin_id,
        )

    async def settings_changed(
        self, key: str, value: str, admin_id: int
    ) -> None:
        await self.log(
            LogEvent.SETTINGS_CHANGED,
            f"تنظیم '{key}' تغییر یافت.",
            admin_id=admin_id,
            extra={"key": key, "new_value": value},
        )

    async def ad_published(
        self, ad_id: int, user_id: int, channel_msg_id: int
    ) -> None:
        await self.log(
            LogEvent.AD_PUBLISHED,
            f"تبلیغ #{ad_id} در کانال منتشر شد.",
            user_id=user_id,
            extra={"ad_id": ad_id, "channel_msg_id": channel_msg_id},
        )

    async def ad_expired(self, ad_id: int, user_id: int) -> None:
        await self.log(
            LogEvent.AD_EXPIRED,
            f"تبلیغ #{ad_id} منقضی و حذف شد.",
            user_id=user_id,
            extra={"ad_id": ad_id},
        )

    async def monthly_reset(self, month: int, year: int) -> None:
        await self.log(
            LogEvent.MONTHLY_RESET,
            f"لیدربرد ماهانه ریست شد — {year}/{month}",
            extra={"year": year, "month": month},
        )