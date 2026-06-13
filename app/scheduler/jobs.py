from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

import jdatetime
import pytz
from aiogram import Bot

from app.core.database import AsyncSessionFactory
from app.services.log_service import LogEvent, LogService
from app.services.queue_service import QueueService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
_TEHRAN = pytz.timezone("Asia/Tehran")


# ═══════════════════════════════════════════════════════════════════════════════
# Job 1 — Meme Publish Queue
# ═══════════════════════════════════════════════════════════════════════════════
async def check_publish_queue_job(bot: Bot) -> None:
    """
    Runs every 5 minutes.
    Publishes next due meme from queue if within publish window
    and queue is not paused.
    """
    try:
        async with AsyncSessionFactory() as session:
            settings_svc = SettingsService(session)

            paused = await settings_svc.get_bool("queue_paused")
            if paused:
                return

            start_hour = await settings_svc.get_int("publish_start_hour", 10)
            end_hour = await settings_svc.get_int("publish_end_hour", 24)

            now_tehran = datetime.now(_TEHRAN)
            effective_end = min(end_hour, 23)

            if not (start_hour <= now_tehran.hour < effective_end):
                return

            queue_svc = QueueService(session)
            now_utc = datetime.now(timezone.utc)
            entry = await queue_svc.get_next_due(now_utc)

            if not entry:
                return

            success = await queue_svc.publish_queue_entry(entry, bot)
            await session.commit()

            if success:
                logger.info("✅ Published meme from queue entry %s", entry.id)

                # Log to channel
                async with AsyncSessionFactory() as log_session:
                    from app.repositories.meme_repo import MemeRepository
                    meme_repo = MemeRepository(log_session)
                    meme = await meme_repo.get_by_id(entry.meme_id)
                    log_svc = LogService(log_session, bot)
                    if meme:
                        from app.repositories.user_repo import UserRepository
                        user_repo = UserRepository(log_session)
                        owner = await user_repo.get_by_id(meme.user_id)
                        u_id = owner.telegram_id if owner else None
                        await log_svc.meme_published(meme.id, u_id or 0)
                        await log_session.commit()
            else:
                logger.warning("❌ Failed to publish queue entry %s", entry.id)

    except Exception as exc:
        logger.error("Error in check_publish_queue_job: %s", exc, exc_info=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Job 2 — Ad Publish Scheduler
# ═══════════════════════════════════════════════════════════════════════════════
async def check_ad_publish_job(bot: Bot) -> None:
    """
    Runs every 10 minutes.
    Publishes banner ads whose publish_at time has arrived.
    Also recalculates publish_at for ads that don't have one yet.
    """
    try:
        async with AsyncSessionFactory() as session:
            from app.repositories.ad_repo import AdRepository
            from app.services.ad_service import AdService

            ad_repo = AdRepository(session)
            ad_svc = AdService(session)
            now_utc = datetime.now(timezone.utc)

            # Publish due ads
            due_ads = await ad_repo.get_due_for_publishing(now_utc)
            for ad in due_ads:
                if ad.ad_type != "banner":
                    continue
                success = await ad_svc.publish_ad(ad, bot)
                if success:
                    logger.info("📢 Published banner ad %s", ad.id)

                    # Log
                    log_svc = LogService(session, bot)
                    from app.repositories.user_repo import UserRepository
                    user_repo = UserRepository(session)
                    owner = await user_repo.get_by_id(ad.user_id)
                    u_id = owner.telegram_id if owner else 0
                    await log_svc.ad_published(
                        ad.id, u_id, ad.channel_message_id or 0
                    )

                    # اطلاع به کاربر
                    if owner:
                        from app.utils.date_helper import time_remaining_fa, to_jalali_full
                        try:
                            text = (
                                f"📢 <b>تبلیغ شما منتشر شد!</b>\n\n"
                                f"🔢 شناسه: <code>#{ad.id}</code>\n"
                                f"📅 زمان انتشار: {to_jalali_full(ad.published_at)}"
                            )
                            if ad.expires_at:
                                text += (
                                    f"\n🔚 پایان نمایش: {to_jalali_full(ad.expires_at)}"
                                    f"\n⏳ {time_remaining_fa(ad.expires_at)} تا پایان نمایش"
                                )
                            await bot.send_message(owner.telegram_id, text)
                        except Exception as exc:
                            logger.warning("اطلاع انتشار تبلیغ ناموفق: %s", exc)

            # Re-schedule ads that have no publish_at yet (waiting for queue slot)
            from sqlalchemy import select
            from app.models.ad import Ad
            unscheduled = await session.execute(
                select(Ad).where(
                    Ad.status == "payment_approved",
                    Ad.publish_at.is_(None),
                    Ad.ad_type == "banner",
                )
            )
            for ad in unscheduled.scalars().all():
                new_time = await ad_svc._calculate_banner_publish_time()
                if new_time:
                    ad.publish_at = new_time
                    logger.info(
                        "Scheduled banner ad %s for %s", ad.id, new_time
                    )

            await session.commit()

    except Exception as exc:
        logger.error("Error in check_ad_publish_job: %s", exc, exc_info=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Job 3 — Ad Expiry Checker
# ═══════════════════════════════════════════════════════════════════════════════
async def check_ad_expiry_job(bot: Bot) -> None:
    """
    Runs every hour.
    Deletes expired ads from channel and marks them as expired.
    """
    try:
        async with AsyncSessionFactory() as session:
            from app.repositories.ad_repo import AdRepository
            from app.services.ad_service import AdService

            ad_repo = AdRepository(session)
            ad_svc = AdService(session)
            now_utc = datetime.now(timezone.utc)

            expired_ads = await ad_repo.get_expired(now_utc)
            for ad in expired_ads:
                await ad_svc.expire_ad(ad, bot)
                logger.info("🗑 Expired ad %s", ad.id)

                log_svc = LogService(session, bot)
                from app.repositories.user_repo import UserRepository
                user_repo = UserRepository(session)
                owner = await user_repo.get_by_id(ad.user_id)
                u_id = owner.telegram_id if owner else 0
                await log_svc.ad_expired(ad.id, u_id)

                # اطلاع به کاربر
                if owner:
                    try:
                        await bot.send_message(
                            owner.telegram_id,
                            f"🔚 <b>مدت نمایش تبلیغ شما به پایان رسید.</b>\n\n"
                            f"🔢 شناسه: <code>#{ad.id}</code>\n"
                            "تبلیغ از کانال حذف شد. در صورت تمایل می‌توانید "
                            "تبلیغ جدیدی ثبت کنید. 🙌",
                        )
                    except Exception as exc:
                        logger.warning("اطلاع پایان تبلیغ ناموفق: %s", exc)

            if expired_ads:
                await session.commit()
                logger.info("Expired %s ads total.", len(expired_ads))

    except Exception as exc:
        logger.error("Error in check_ad_expiry_job: %s", exc, exc_info=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Job 4 — Banner Ad Auto-Reply
# ═══════════════════════════════════════════════════════════════════════════════
async def check_ad_reply_job(bot: Bot) -> None:
    """
    Runs every 2 minutes.
    Sends auto-reply for banner ads that have been published
    and are due for their reply (10-15 min after publish).
    """
    try:
        async with AsyncSessionFactory() as session:
            from app.repositories.ad_repo import AdRepository
            from app.services.ad_service import AdService

            ad_repo = AdRepository(session)
            ad_svc = AdService(session)
            now_utc = datetime.now(timezone.utc)

            pending_reply_ads = await ad_repo.get_pending_reply(now_utc)
            for ad in pending_reply_ads:
                success = await ad_svc.send_auto_reply(ad, bot)
                if success:
                    logger.info("💬 Auto-reply sent for ad %s", ad.id)

            if pending_reply_ads:
                await session.commit()

    except Exception as exc:
        logger.error("Error in check_ad_reply_job: %s", exc, exc_info=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Job 5 — Monthly Leaderboard Reset
# ═══════════════════════════════════════════════════════════════════════════════
async def reset_monthly_leaderboard_job() -> None:
    """
    Runs daily at 00:05 Tehran time.
    Resets monthly_tokens for all users on 1st of each Jalali month.
    """
    try:
        today_jalali = jdatetime.date.today()
        if today_jalali.day != 1:
            return

        async with AsyncSessionFactory() as session:
            user_svc = UserService(session)
            await user_svc.reset_all_monthly_tokens()

            log_svc = LogService(session)
            await log_svc.monthly_reset(
                month=today_jalali.month,
                year=today_jalali.year,
            )
            await session.commit()

        logger.info(
            "🔄 Monthly leaderboard reset — Jalali %s/%s",
            today_jalali.year,
            today_jalali.month,
        )

    except Exception as exc:
        logger.error(
            "Error in reset_monthly_leaderboard_job: %s", exc, exc_info=True
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Job 6 — Daily Meme Count Reset (optional safety net)
# ═══════════════════════════════════════════════════════════════════════════════
async def reset_daily_meme_counts_job() -> None:
    """
    Runs every day at 00:01 Tehran time.
    Resets daily_meme_count for all users.
    The main reset logic is inline (checks last_meme_date),
    but this is a safety net to avoid drift.
    """
    try:
        async with AsyncSessionFactory() as session:
            from sqlalchemy import update
            from app.models.user import User
            await session.execute(
                update(User).values(daily_meme_count=0)
            )
            await session.commit()
        logger.info("✅ Daily meme counts reset.")
    except Exception as exc:
        logger.error("Error in reset_daily_meme_counts_job: %s", exc, exc_info=True)
