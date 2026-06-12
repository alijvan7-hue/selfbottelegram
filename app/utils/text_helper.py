from __future__ import annotations


def fa_number(n: int | float) -> str:
    """Format a number with thousands separator."""
    if isinstance(n, float):
        return f"{n:,.0f}"
    return f"{n:,}"


def truncate(text: str, max_len: int = 200) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )