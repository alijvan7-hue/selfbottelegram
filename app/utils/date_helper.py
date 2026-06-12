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


def now_tehran() -> datetime:
    return datetime.now(_TEHRAN)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def jalali_now_str() -> str:
    return to_jalali(now_utc())