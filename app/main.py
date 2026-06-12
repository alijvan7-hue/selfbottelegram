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
    from app.handlers.admin.guide import router as guide_router  # ← جدید

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
        guide_router,  # ← جدید
    )