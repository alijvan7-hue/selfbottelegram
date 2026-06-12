from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from app.core.bot import bot, dp
from app.core.config import config
from app.core.database import AsyncSessionFactory, dispose_engine

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    level = logging.DEBUG if config.debug else logging.INFO
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    logging.basicConfig(
        level=level,
        format=fmt,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.scheduler").setLevel(logging.WARNING)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def _register_routers(dispatcher: Dispatcher) -> None:
    from app.handlers.common import router as common_router
    from app.handlers.meme import router as meme_router
    from app.handlers.profile import router as profile_router
    from app.handlers.leaderboard import router as leaderboard_router
    from app.handlers.support import router as support_router
    from app.handlers.payment import router as payment_router
    from app.handlers.ads.menu import router as ads_menu_router
    from app.handlers.ads.banner import router as banner_router
    from app.handlers.ads.oneliner import router as oneliner_router
    from app.handlers.admin.panel import router as admin_panel_router
    from app.handlers.admin.meme_moderation import router as meme_mod_router
    from app.handlers.admin.ad_moderation import router as ad_mod_router
    from app.handlers.admin.queue_management import router as queue_router
    from app.handlers.admin.user_management import router as user_mgmt_router
    from app.handlers.admin.settings_management import router as settings_router
    from app.handlers.admin.revenue import router as revenue_router
    from app.handlers.admin.statistics import router as stats_router
    from app.handlers.admin.logs import router as logs_router
    from app.handlers.admin.guide import router as guide_router

    dispatcher.include_routers(
        common_router,
        meme_router,
        profile_router,
        leaderboard_router,
        support_router,
        payment_router,
        ads_menu_router,
        banner_router,
        oneliner_router,
        admin_panel_router,
        meme_mod_router,
        ad_mod_router,
        queue_router,
        user_mgmt_router,
        settings_router,
        revenue_router,
        stats_router,
        logs_router,
        guide_router,
    )


def _register_middlewares(dispatcher: Dispatcher) -> None:
    from app.middlewares.auth import AuthMiddleware
    from app.middlewares.throttle import ThrottleMiddleware

    dispatcher.message.middleware(AuthMiddleware())
    dispatcher.callback_query.middleware(AuthMiddleware())
    dispatcher.message.middleware(ThrottleMiddleware(rate_limit=1.0))


async def _set_bot_commands(bot_instance: Bot) -> None:
    user_commands = [
        BotCommand(command="start", description="شروع / منوی اصلی"),
        BotCommand(command="help", description="راهنما"),
    ]
    admin_commands = [
        BotCommand(command="start", description="شروع"),
        BotCommand(command="admin", description="پنل ادمین"),
        BotCommand(command="guide", description="راهنمای ادمین"),
        BotCommand(command="stats", description="آمار کلی"),
        BotCommand(command="revenue", description="گزارش درآمد"),
        BotCommand(command="logs", description="لاگ‌های اخیر"),
        BotCommand(command="publish_now", description="انتشار فوری /publish_now ID"),
        BotCommand(command="pause_queue", description="توقف صف"),
        BotCommand(command="resume_queue", description="ادامه صف"),
        BotCommand(command="lock", description="قفل ربات"),
        BotCommand(command="unlock", description="باز کردن قفل"),
        BotCommand(command="ban", description="بن کاربر /ban ID 7d|30d|permanent"),
        BotCommand(command="unban", description="رفع بن /unban ID"),
        BotCommand(command="addtoken", description="افزایش توکن /addtoken ID amount"),
        BotCommand(command="removetoken", description="کاهش توکن /removetoken ID amount"),
        BotCommand(command="setlimit", description="تنظیم محدودیت /setlimit ID n|unlimited"),
        BotCommand(command="user", description="اطلاعات کاربر /user ID"),
        BotCommand(command="set", description="تغییر تنظیم /set key value"),
        BotCommand(command="addlevel", description="افزودن سطح /addlevel name tokens"),
        BotCommand(command="dellevel", description="حذف سطح /dellevel ID"),
        BotCommand(command="adddiscount", description="افزودن تخفیف"),
        BotCommand(command="deldiscount", description="حذف تخفیف /deldiscount code"),
        BotCommand(command="togglediscount", description="فعال/غیرفعال /togglediscount code"),
        BotCommand(command="userlogs", description="لاگ کاربر /userlogs ID"),
    ]

    await bot_instance.set_my_commands(user_commands)

    for admin_id in config.admin_ids:
        try:
            from aiogram.types import BotCommandScopeChat
            await bot_instance.set_my_commands(
                admin_commands,
                scope=BotCommandScopeChat(chat_id=admin_id),
            )
        except Exception as exc:
            logger.warning("Could not set admin commands for %s: %s", admin_id, exc)


async def on_startup() -> None:
    logger.info("🚀 Bot starting up …")

    from app.core.database import create_all_tables
    await create_all_tables()

    from app.scheduler.setup import start_scheduler
    await start_scheduler(bot)

    await _set_bot_commands(bot)

    for admin_id in config.admin_ids:
        try:
            await bot.send_message(
                admin_id,
                "✅ <b>ربات راه‌اندازی شد.</b>\n\n"
                "🔐 /admin — پنل ادمین\n"
                "📖 /guide — راهنمای کامل",
            )
        except Exception:
            pass

    logger.info("✅ Bot started successfully.")


async def on_shutdown() -> None:
    logger.info("🔄 Bot shutting down …")

    from app.scheduler.setup import stop_scheduler
    await stop_scheduler()

    await dispose_engine()
    await bot.session.close()
    logger.info("✅ Bot shut down cleanly.")


async def main() -> None:
    _setup_logging()
    _register_middlewares(dp)
    _register_routers(dp)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
    )


if __name__ == "__main__":
    asyncio.run(main())        settings_router,
        revenue_router,
        stats_router,
        logs_router,
        guide_router,  # ← جدید
    )
