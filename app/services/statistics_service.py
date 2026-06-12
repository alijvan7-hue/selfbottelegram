from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional

import jdatetime
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ad import Ad
from app.models.meme import Meme
from app.models.revenue import RevenueLog
from app.models.user import User
from app.repositories.revenue_repo import RevenueRepository
from app.repositories.user_repo import UserRepository


class StatisticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._revenue_repo = RevenueRepository(session)
        self._user_repo = UserRepository(session)

    # ── User stats ────────────────────────────────────────────────────────
    async def get_user_full_stats(self, user_id: int) -> Dict:
        # Meme counts
        meme_total = await self._count(Meme, Meme.user_id == user_id)
        meme_approved = await self._count(
            Meme, Meme.user_id == user_id, Meme.status == "approved"
        )
        meme_rejected = await self._count(
            Meme, Meme.user_id == user_id, Meme.status == "rejected"
        )
        meme_pending = await self._count(
            Meme, Meme.user_id == user_id, Meme.status == "pending"
        )

        # Ad counts
        ad_total = await self._count(Ad, Ad.user_id == user_id)
        ad_approved = await self._count(
            Ad, Ad.user_id == user_id, Ad.status.in_(["approved", "payment_approved", "published", "expired"])
        )

        return {
            "meme_total": meme_total,
            "meme_approved": meme_approved,
            "meme_rejected": meme_rejected,
            "meme_pending": meme_pending,
            "ad_total": ad_total,
            "ad_approved": ad_approved,
        }

    async def _count(self, model, *conditions) -> int:
        stmt = select(func.count()).select_from(model)
        for cond in conditions:
            stmt = stmt.where(cond)
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    # ── Global stats ──────────────────────────────────────────────────────
    async def get_global_stats(self) -> Dict:
        total_users = await self._count(User)
        total_memes = await self._count(Meme)
        approved_memes = await self._count(Meme, Meme.status == "approved")
        published_memes = await self._count(Meme, Meme.is_published.is_(True))
        total_ads = await self._count(Ad)
        published_ads = await self._count(Ad, Ad.status.in_(["published", "expired"]))

        revenue_repo = self._revenue_repo
        revenue_today = await revenue_repo.today(date.today())
        revenue_total = await revenue_repo.total()

        return {
            "total_users": total_users,
            "total_memes": total_memes,
            "approved_memes": approved_memes,
            "published_memes": published_memes,
            "total_ads": total_ads,
            "published_ads": published_ads,
            "revenue_today": revenue_today,
            "revenue_total": revenue_total,
        }

    # ── Revenue breakdown ─────────────────────────────────────────────────
    async def get_revenue_breakdown(self) -> Dict:
        today = date.today()
        week_start = today - timedelta(days=6)
        month_start = today.replace(day=1)

        today_rev = await self._revenue_repo.today(today)
        week_rev = await self._revenue_repo.total_by_date_range(week_start, today)
        month_rev = await self._revenue_repo.total_by_date_range(month_start, today)
        total_rev = await self._revenue_repo.total()

        # By type
        banner_total = await self._revenue_by_type("banner")
        oneliner_total = await self._revenue_by_type("oneliner")

        return {
            "today": today_rev,
            "week": week_rev,
            "month": month_rev,
            "total": total_rev,
            "banner_total": banner_total,
            "oneliner_total": oneliner_total,
        }

    async def _revenue_by_type(self, ad_type: str) -> float:
        stmt = select(
            func.coalesce(func.sum(RevenueLog.amount), 0)
        ).where(RevenueLog.type == ad_type)
        result = await self._session.execute(stmt)
        return float(result.scalar_one())

    # ── Top earners ───────────────────────────────────────────────────────
    async def get_top_earners(self, limit: int = 10) -> List[Dict]:
        stmt = (
            select(
                RevenueLog.user_id,
                func.sum(RevenueLog.amount).label("total"),
            )
            .group_by(RevenueLog.user_id)
            .order_by(func.sum(RevenueLog.amount).desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        out = []
        for row in rows:
            user = await self._user_repo.get_by_id(row.user_id) if row.user_id else None
            out.append({
                "user": user,
                "total": float(row.total),
            })
        return out

    # ── Jalali month revenue ──────────────────────────────────────────────
    async def get_jalali_month_revenue(self) -> float:
        today_j = jdatetime.date.today()
        # First day of current Jalali month → Gregorian
        jalali_first = jdatetime.date(today_j.year, today_j.month, 1)
        greg_first = jalali_first.togregorian()
        today_g = date.today()
        return await self._revenue_repo.total_by_date_range(greg_first, today_g)

    # ── Meme approval rate ────────────────────────────────────────────────
    async def get_meme_approval_rate(self) -> float:
        total = await self._count(
            Meme,
            Meme.status.in_(["approved", "rejected"]),
        )
        if total == 0:
            return 0.0
        approved = await self._count(Meme, Meme.status == "approved")
        return round((approved / total) * 100, 1)

    # ── New users today ───────────────────────────────────────────────────
    async def get_new_users_today(self) -> int:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return await self._count(User, User.joined_at >= today_start)