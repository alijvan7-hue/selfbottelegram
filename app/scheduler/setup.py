from __future__ import annotations

import logging
from typing import Optional

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler: Optional[AsyncIOScheduler] = None


async def start_scheduler(bot: Bot) -> None:
    global _scheduler

    _scheduler = AsyncIOScheduler(timezone="Asia/Tehran")

    from app.scheduler.jobs import (
        check_publish_queue_job,
        check_ad_publish_job,
        check_ad_expiry_job,
        check_ad_reply_job,
        reset_monthly_leaderboard_job,
        reset_daily_meme_counts_job,
    )

    # ── Meme queue: every 5 min ───────────────────────────────────────────
    _scheduler.add_job(
        check_publish_queue_job,
        trigger=IntervalTrigger(minutes=5),
        args=[bot],
        id="publish_queue",
        replace_existing=True,
        misfire_grace_time=60,
        max_instances=1,
    )

    # ── Ad publish: every 10 min ──────────────────────────────────────────
    _scheduler.add_job(
        check_ad_publish_job,
        trigger=IntervalTrigger(minutes=10),
        args=[bot],
        id="ad_publish",
        replace_existing=True,
        misfire_grace_time=120,
        max_instances=1,
    )

    # ── Ad expiry: every 1 hour ───────────────────────────────────────────
    _scheduler.add_job(
        check_ad_expiry_job,
        trigger=IntervalTrigger(hours=1),
        args=[bot],
        id="ad_expiry",
        replace_existing=True,
        misfire_grace_time=300,
        max_instances=1,
    )

    # ── Ad auto-reply: every 2 min ────────────────────────────────────────
    _scheduler.add_job(
        check_ad_reply_job,
        trigger=IntervalTrigger(minutes=2),
        args=[bot],
        id="ad_reply",
        replace_existing=True,
        misfire_grace_time=60,
        max_instances=1,
    )

    # ── Monthly reset: daily at 00:05 Tehran ──────────────────────────────
    _scheduler.add_job(
        reset_monthly_leaderboard_job,
        trigger=CronTrigger(hour=0, minute=5, timezone="Asia/Tehran"),
        id="monthly_reset",
        replace_existing=True,
        misfire_grace_time=3600,
        max_instances=1,
    )

    # ── Daily meme count reset: daily at 00:01 Tehran ────────────────────
    _scheduler.add_job(
        reset_daily_meme_counts_job,
        trigger=CronTrigger(hour=0, minute=1, timezone="Asia/Tehran"),
        id="daily_meme_reset",
        replace_existing=True,
        misfire_grace_time=3600,
        max_instances=1,
    )

    _scheduler.start()
    logger.info(
        "✅ APScheduler started with %s jobs.",
        len(_scheduler.get_jobs()),
    )


async def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")


def get_scheduler() -> Optional[AsyncIOScheduler]:
    return _scheduler