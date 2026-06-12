from __future__ import annotations

import re


def is_valid_url(url: str) -> bool:
    pattern = re.compile(
        r"^(https?://)?"
        r"([\w\-]+\.)+[\w\-]+"
        r"(/[\w\-._~:/?#[\]@!$&\'()*+,;=%]*)?"
        r"$",
        re.IGNORECASE,
    )
    return bool(pattern.match(url))


def is_valid_telegram_link(url: str) -> bool:
    return url.startswith("https://t.me/") or url.startswith("http://t.me/")