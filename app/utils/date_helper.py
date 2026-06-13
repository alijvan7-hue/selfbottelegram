from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import jdatetime
import pytz

_TEHRAN = pytz.timezone("Asia/Tehran")


def to_jalali(dt: Optional[datetime]) -> str:
    """Convert UTC or timezone-aware datetime to Jalali string."""
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local_dt = dt.astimezone(_TEHRAN)
    jdt = jdatetime.datetime.fromgregorian(datetime=local_dt)
    return jdt.strftime("%Y/%m/%d %H:%M")


_WEEKDAYS_FA = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]


def to_jalali_full(dt: Optional[datetime]) -> str:
    """مثل: سه‌شنبه ۱۴۰۳/۰۴/۰۲ — ساعت ۱۸:۳۰"""
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local_dt = dt.astimezone(_TEHRAN)
    jdt = jdatetime.datetime.fromgregorian(datetime=local_dt)
    weekday = _WEEKDAYS_FA[jdt.weekday()]
    return f"{weekday} {jdt.strftime('%Y/%m/%d')} — ساعت {jdt.strftime('%H:%M')}"


def time_remaining_fa(target: Optional[datetime]) -> str:
    """مثل: ۲ روز و ۵ ساعت — زمان باقی‌مانده تا یک لحظه مشخص."""
    if target is None:
        return "—"
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    total_minutes = int((target - now).total_seconds() // 60)
    if total_minutes <= 0:
        return "کمتر از یک دقیقه"

    days, rem = divmod(total_minutes, 1440)
    hours, minutes = divmod(rem, 60)

    parts = []
    if days:
        parts.append(f"{days} روز")
    if hours:
        parts.append(f"{hours} ساعت")
    if minutes and not days:
        parts.append(f"{minutes} دقیقه")

    return " و ".join(parts) if parts else "کمتر از یک دقیقه"


def now_tehran() -> datetime:
    return datetime.now(_TEHRAN)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def jalali_now_str() -> str:
    return to_jalali(now_utc())
