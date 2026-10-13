"""جلسهٔ معاملاتی بورس تهران. شنبه تا چهارشنبه، حدود ۹ تا ۱۲:۳۰."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

TEHRAN = ZoneInfo("Asia/Tehran")

# Python weekday: Monday=0 ... Sunday=6. Tehran trades Sat–Wed.
OPEN_WEEKDAYS = {5, 6, 0, 1, 2}
PREOPEN = (8 * 60 + 45, 9 * 60)
CONTINUOUS = (9 * 60, 12 * 60 + 30)
TAL = (12 * 60 + 45, 13 * 60)


def tehran_now(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(TEHRAN)
    if now.tzinfo is None:
        return now.replace(tzinfo=TEHRAN)
    return now.astimezone(TEHRAN)


def market_phase(now: datetime | None = None) -> str:
    """preopen | open | tal | closed.

    ساعات رسمی ممکن است با مصوبه عوض شود. اگر خوراک زنده پرچم باز/بسته بدهد، همان مقدم است.
    """

    current = tehran_now(now)
    if current.weekday() not in OPEN_WEEKDAYS:
        return "closed"
    minutes = current.hour * 60 + current.minute
    if PREOPEN[0] <= minutes < PREOPEN[1]:
        return "preopen"
    if CONTINUOUS[0] <= minutes < CONTINUOUS[1]:
        return "open"
    if TAL[0] <= minutes < TAL[1]:
        return "tal"
    return "closed"


def phase_label(phase: str) -> str:
    return {
        "preopen": "پیش‌گشایش",
        "open": "بازار باز است",
        "tal": "معاملات پایانی",
        "closed": "بازار بسته است",
        "unknown": "وضعیت نامشخص",
    }.get(phase, phase)
