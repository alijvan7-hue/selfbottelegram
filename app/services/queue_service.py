from __future__ import annotations

import logging
import random
from datetime import date, datetime, timedelta, timezone
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

    # ── افزودن به صف ──────────────────────────────────────────────────────
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
        now_local = datetime.now(_TEHRAN)

        if waiting:
            last_time = max(e.scheduled_time for e in waiting)
            last_local = last_time.astimezone(_TEHRAN)
        else:
            candidate = now_local.replace(
                hour=start_hour, minute=0, second=0, microsecond=0
            )
            last_local = candidate if candidate > now_local else now_local

        interval = random.randint(min_interval, max_interval)
        scheduled_local = last_local + timedelta(minutes=interval)
        scheduled_local = self._clamp_to_window(scheduled_local, start_hour, end_hour)
        scheduled_utc = scheduled_local.astimezone(timezone.utc)

        entry = await self._repo.create(
            meme_id=meme_id,
            scheduled_time=scheduled_utc,
            status="waiting",
        )
        logger.info("میم %s به صف اضافه شد: %s", meme_id, scheduled_utc)
        return entry

    def _clamp_to_window(
        self,
        dt: datetime,
        start_hour: int,
        end_hour: int,
    ) -> datetime:
        effective_end = min(end_hour, 23)
        if dt.hour < start_hour:
            dt = dt.replace(
                hour=start_hour,
                minute=random.randint(0, 59),
                second=0,
                microsecond=0,
            )
        elif dt.hour >= effective_end:
            dt = (dt + timedelta(days=1)).replace(
                hour=start_hour,
                minute=random.randint(0, 59),
                second=0,
                microsecond=0,
            )
        return dt

    # ── بازچینی صف ────────────────────────────────────────────────────────
    async def reorder_queue(self, settings_svc: SettingsService) -> None:
        """
        بعد از حذف یا تغییر، تمام آیتم‌های صف را دوباره زمان‌بندی می‌کند
        تا فاصله‌ها یکدست باشند.
        """
        start_hour = await settings_svc.get_int("publish_start_hour", 10)
        end_hour = await settings_svc.get_int("publish_end_hour", 24)
        min_interval = await settings_svc.get_int("min_publish_interval", 60)
        max_interval = await settings_svc.get_int("max_publish_interval", 120)

        waiting = await self._repo.get_waiting()
        if not waiting:
            return

        # مرتب‌سازی بر اساس زمان فعلی
        waiting.sort(key=lambda e: e.scheduled_time)

        now_local = datetime.now(_TEHRAN)
        next_time = now_local

        # اگر اولین زمان در گذشته است یا خارج از window، از الان شروع کن
        candidate = now_local.replace(
            hour=start_hour, minute=0, second=0, microsecond=0
        )
        if candidate > now_local:
            next_time = candidate

        for entry in waiting:
            interval = random.randint(min_interval, max_interval)
            next_time = next_time + timedelta(minutes=interval)
            next_time = self._clamp_to_window(next_time, start_hour, end_hour)
            entry.scheduled_time = next_time.astimezone(timezone.utc)
            await self._repo.save(entry)

        logger.info("صف بازچینی شد. %s آیتم.", len(waiting))

        # تبلیغات بنری زمان‌بندی‌شده را هم با صف جدید هماهنگ کن
        await self._reorder_banner_ads(waiting)

    # ── هماهنگ‌سازی تبلیغات بنری با صف جدید ────────────────────────────────
    async def _reorder_banner_ads(self, waiting: List[PublishQueue]) -> None:
        """
        هر تبلیغ بنری باید نیم ساعت قبل از یک پست در بازه ساعت ۱۷ تا ۲۰ منتشر شود
        (حداکثر یک تبلیغ در روز). ترتیب فعلی تبلیغات (بر اساس publish_at قبلی)
        تا حد امکان حفظ می‌شود؛ فقط زمانشان با صف جدید هماهنگ می‌شود.
        """
        from app.repositories.ad_repo import AdRepository

        ad_repo = AdRepository(self._session)
        ads = await ad_repo.get_scheduled()
        if not ads:
            return

        # برای هر روز، اولین پست داخل بازه ۱۷-۲۰ را پیدا کن
        window_posts: dict[date, datetime] = {}
        for entry in waiting:
            hour = entry.scheduled_time.hour
            if 17 <= hour < 20:
                day = entry.scheduled_time.date()
                if day not in window_posts or entry.scheduled_time < window_posts[day]:
                    window_posts[day] = entry.scheduled_time

        available_days = sorted(window_posts.keys())
        if not available_days:
            return

        for i, ad in enumerate(ads):
            if i >= len(available_days):
                break  # تبلیغات بیشتر از روزهای دارای پست در بازه؛ بقیه دست‌نخورده می‌مانند
            day = available_days[i]
            ad.publish_at = window_posts[day] - timedelta(minutes=30)
            await ad_repo.save(ad)

    # ── گرفتن بعدی قابل انتشار ───────────────────────────────────────────
    async def get_next_due(self, now: datetime) -> Optional[PublishQueue]:
        return await self._repo.get_next_due(now)

    # ── همه در صف ─────────────────────────────────────────────────────────
    async def get_all_waiting(self) -> List[PublishQueue]:
        return await self._repo.get_waiting()

    # ── لغو آیتم + بازچینی ───────────────────────────────────────────────
    async def cancel_queue_entry(
        self,
        queue_id: int,
        settings_svc: Optional[SettingsService] = None,
    ) -> bool:
        entry = await self._repo.get_by_id(queue_id)
        if not entry:
            return False
        entry.status = "cancelled"
        await self._repo.save(entry)

        # بازچینی خودکار
        if settings_svc:
            await self.reorder_queue(settings_svc)

        return True

    # ── انتشار فوری ──────────────────────────────────────────────────────
    async def publish_immediately(self, meme: Meme, bot: Bot) -> bool:
        if not config.channel_id:
            logger.error("CHANNEL_ID تنظیم نشده.")
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

            logger.info("میم %s منتشر شد. پیام: %s", meme.id, sent.message_id)
            return True

        except Exception as exc:
            logger.error("خطا در انتشار میم %s: %s", meme.id, exc)
            return False

    async def _send_to_channel(self, bot: Bot, meme: Meme):
        # گرفتن کپشن هوشمند
        from app.services.settings_service import SettingsService
        svc = SettingsService(self._session)
        smart_caption = await svc.get("smart_caption") or "✖️Check it:\n➡️@Teriak18"

        if meme.file_type == "photo":
            return await bot.send_photo(
                config.channel_id,
                photo=meme.file_id,
                caption=smart_caption,
            )
        elif meme.file_type == "video":
            return await bot.send_video(
                config.channel_id,
                video=meme.file_id,
                caption=smart_caption,
            )
        else:
            return await bot.send_animation(
                config.channel_id,
                animation=meme.file_id,
                caption=smart_caption,
            )

    # ── انتشار آیتم صف ───────────────────────────────────────────────────
    async def publish_queue_entry(self, entry: PublishQueue, bot: Bot) -> bool:
        meme_repo = MemeRepository(self._session)
        meme = await meme_repo.get_by_id(entry.meme_id)
        if not meme:
            entry.status = "cancelled"
            await self._repo.save(entry)
            return False
        if meme.is_published:
            entry.status = "published"
            await self._repo.save(entry)
            return False
        return await self.publish_immediately(meme, bot)

    # ── تعداد در صف ──────────────────────────────────────────────────────
    async def count_waiting(self) -> int:
        return await self._repo.count_waiting()

    # ── گرفتن آیتم بر اساس meme_id ──────────────────────────────────────
    async def get_by_meme_id(self, meme_id: int) -> Optional[PublishQueue]:
        return await self._repo.get_by_meme_id(meme_id)

    # ── نزدیک‌ترین پست در بازه تبلیغ ────────────────────────────────────
    async def get_next_in_ad_window(self) -> Optional[PublishQueue]:
        return await self._repo.get_next_in_window(17, 20)
