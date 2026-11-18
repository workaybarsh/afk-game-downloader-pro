"""Small formatting helpers (sizes, speeds, durations) - language aware."""

from __future__ import annotations

import time

from .i18n import tr


def fmt_bytes(n: float | int | None) -> str:
    if n is None:
        return "—"
    n = float(n)
    if n < 0:
        return "—"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while n >= 1024.0 and i < len(units) - 1:
        n /= 1024.0
        i += 1
    if i == 0:
        return f"{int(n)} B"
    return f"{n:.2f} {units[i]}" if n < 100 else f"{n:.1f} {units[i]}"


def fmt_speed(bps: float | int | None) -> str:
    if not bps or bps <= 0:
        return "—"
    return fmt_bytes(bps) + tr("unit.per_second")


def fmt_duration(sec: float | None) -> str:
    if sec is None:
        return "—"
    try:
        sec = float(sec)
    except (TypeError, ValueError):
        return "—"
    if sec != sec or sec <= 0 or sec > 86400 * 30:
        return "—"
    sec = int(sec)
    if sec < 60:
        return tr("dur.seconds", s=sec)
    minutes, seconds = divmod(sec, 60)
    if minutes < 60:
        return tr("dur.minutes", m=minutes, s=seconds)
    hours, minutes = divmod(minutes, 60)
    return tr("dur.hours", h=hours, m=minutes)


def clock(ts: float | None = None) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts if ts is not None else time.time()))


def ago(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    if seconds < 2:
        return tr("time.now")
    if seconds < 60:
        return tr("time.sec_ago", n=int(seconds))
    if seconds < 3600:
        return tr("time.min_ago", n=int(seconds // 60))
    return tr("time.hour_ago", n=int(seconds // 3600))


def pct(value: float) -> str:
    """Percent sign position differs between English and Turkish."""
    if value is None or value != value:
        return "—"
    from .i18n import get_lang

    return f"{value * 100:.1f}%" if get_lang() == "en" else f"%{value * 100:.1f}"
