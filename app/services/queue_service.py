from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import pytz
from aiogram import Bot

from app.core.config import config
from app.models.meme import Meme
from app.models.queue import PublishQueue
from app.repositories.meme_repo import MemeRepository
from app.repositories.queue_repo import QueueRepository
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

_TEHRAN = pytz.timezone("Asia/Tehran")


class QueueService:
    def __init__(self, session) -> None:
        self._repo = QueueRepository(session)
        self._session = session

    # ── Add to queue ──────────────────────────────────────────────────────
    async def add_to_queue(
        self,
        meme_id: int,
        settings_svc: SettingsService,
    ) -> Optional[PublishQueue]:
        start_hour = await settings_svc.get_int("publish_start_hour", 10)
        end_hour = await settings_svc.get_int("publish_end_hour", 24)
        min_interval = await settings_svc.get_int("min_publish_interval", 60)
        max_interval = await settings_svc.get_int("max_publish_interval", 120)

        waiting = await self._repo.get_waiting()
        now_tehran = datetime.now(_TEHRAN)

        if waiting:
            last_scheduled = max(e.scheduled_time for e in waiting)
            last_local = last_scheduled.astimezone(_TEHRAN)
        else:
            candidate = now_tehran.replace(
                hour=start_hour, minute=0, second=0, microsecond=0
            )
            last_local = candidate if candidate > now_tehran else now_tehran

        interval_minutes = random.randint(min_interval, max_interval)
        scheduled_local = last_local + timedelta(minutes=interval_minutes)
        scheduled_local = self._clamp_to_window(
            scheduled_local, start_hour, end_hour
        )
        scheduled_utc = scheduled_local.astimezone(timezone.utc)

        entry = await self._repo.create(
            meme_id=meme_id,
            scheduled_time=scheduled_utc,
            status="waiting",
        )
        logger.info(
            "Meme %s added to queue. Scheduled: %s",
            meme_id,
            scheduled_utc.isoformat(),
        )
        return entry

    # ── Clamp to publish window ───────────────────────────────────────────
    def _clamp_to_window(
        self,
        dt: datetime,
        start_hour: int,
        end_hour: int,
    ) -> datetime:
        effective_end = min(end_hour, 23)
        if dt.hour < start_hour:
            dt = dt.replace(
                hour=start_hour, minute=random.randint(0, 59),
                second=0, microsecond=0
            )
        elif dt.hour >= effective_end:
            dt = (dt + timedelta(days=1)).replace(
                hour=start_hour, minute=random.randint(0, 59),
                second=0, microsecond=0
            )
        return dt

    # ── Fetch next due entry ──────────────────────────────────────────────
    async def get_next_due(self, now: datetime) -> Optional[PublishQueue]:
        return await self._repo.get_next_due(now)

    # ── Fetch all waiting ─────────────────────────────────────────────────
    async def get_all_waiting(self) -> List[PublishQueue]:
        return await self._repo.get_waiting()

    # ── Cancel entry ──────────────────────────────────────────────────────
    async def cancel_queue_entry(self, queue_id: int) -> bool:
        entry = await self._repo.get_by_id(queue_id)
        if not entry:
            return False
        entry.status = "cancelled"
        await self._repo.save(entry)
        return True

    # ── Publish immediately ───────────────────────────────────────────────
    async def publish_immediately(self, meme: Meme, bot: Bot) -> bool:
        if not config.channel_id:
            logger.error("CHANNEL_ID not configured.")
            return False
        try:
            sent = await self._send_to_channel(bot, meme)
            if not sent:
                return False

            meme_repo = MemeRepository(self._session)
            db_meme = await meme_repo.get_by_id(meme.id)
            if db_meme:
                now = datetime.now(timezone.utc)
                db_meme.is_published = True
                db_meme.published_at = now
                db_meme.channel_message_id = sent.message_id
                db_meme.updated_at = now
                await meme_repo.save(db_meme)

            queue_entry = await self._repo.get_by_meme_id(meme.id)
            if queue_entry:
                queue_entry.status = "published"
                await self._repo.save(queue_entry)

            logger.info("Meme %s published to channel. Message ID: %s", meme.id, sent.message_id)
            return True

        except Exception as exc:
            logger.error("Failed to publish meme %s: %s", meme.id, exc)
            return False

    async def _send_to_channel(self, bot: Bot, meme: Meme):
        if meme.file_type == "photo":
            return await bot.send_photo(config.channel_id, photo=meme.file_id)
        elif meme.file_type == "video":
            return await bot.send_video(config.channel_id, video=meme.file_id)
        else:
            return await bot.send_animation(config.channel_id, animation=meme.file_id)

    # ── Publish queue entry ───────────────────────────────────────────────
    async def publish_queue_entry(self, entry: PublishQueue, bot: Bot) -> bool:
        meme_repo = MemeRepository(self._session)
        meme = await meme_repo.get_by_id(entry.meme_id)
        if not meme:
            logger.warning("Meme %s not found for queue entry %s", entry.meme_id, entry.id)
            entry.status = "cancelled"
            await self._repo.save(entry)
            return False
        if meme.is_published:
            entry.status = "published"
            await self._repo.save(entry)
            return False
        return await self.publish_immediately(meme, bot)

    # ── Count waiting ─────────────────────────────────────────────────────
    async def count_waiting(self) -> int:
        return await self._repo.count_waiting()

    # ── Get entry by meme_id ──────────────────────────────────────────────
    async def get_by_meme_id(self, meme_id: int) -> Optional[PublishQueue]:
        return await self._repo.get_by_meme_id(meme_id)

    # ── Reschedule entry ──────────────────────────────────────────────────
    async def reschedule(
        self,
        queue_id: int,
        new_time: datetime,
    ) -> bool:
        entry = await self._repo.get_by_id(queue_id)
        if not entry or entry.status != "waiting":
            return False
        entry.scheduled_time = new_time
        await self._repo.save(entry)
        return True

    # ── Next queue entry inside ad window (17-20) ─────────────────────────
    async def get_next_in_ad_window(self) -> Optional[PublishQueue]:
        return await self._repo.get_next_in_window(17, 20)