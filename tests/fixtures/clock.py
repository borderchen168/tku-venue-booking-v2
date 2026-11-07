"""測試用時鐘：`FixedClock` 與 `fixed_clock` fixture（overview.md 2.1）。"""

import datetime as dt
from zoneinfo import ZoneInfo

import pytest

TAIPEI = ZoneInfo('Asia/Taipei')

# 2026-11-09（週一）10:00 台北時間
DEFAULT_FIXED_NOW_UTC = dt.datetime(2026, 11, 9, 2, 0, tzinfo=dt.UTC)


class FixedClock:
    """固定時間的 Clock；可用 `set_now` 推進時間。"""

    def __init__(self, now_utc: dt.datetime, tz: ZoneInfo) -> None:
        self._tz = tz
        self._now = self._validate(now_utc)

    @staticmethod
    def _validate(now_utc: dt.datetime) -> dt.datetime:
        if now_utc.tzinfo is None or now_utc.utcoffset() is None:
            raise ValueError('FixedClock 不接受 naive datetime')
        return now_utc.astimezone(dt.UTC)

    def set_now(self, now_utc: dt.datetime) -> None:
        """改變目前時間（測試逾時等情境）。"""
        self._now = self._validate(now_utc)

    def advance(self, delta: dt.timedelta) -> None:
        """時間往後推進 `delta`。"""
        self._now += delta

    def now_utc(self) -> dt.datetime:
        """固定的目前時間（aware UTC）。"""
        return self._now

    def today_local(self) -> dt.date:
        """固定時間在 tz 的日期。"""
        return self._now.astimezone(self._tz).date()


@pytest.fixture
def fixed_clock() -> FixedClock:
    """固定在 2026-11-09（週一）10:00 台北時間的時鐘。"""
    return FixedClock(DEFAULT_FIXED_NOW_UTC, TAIPEI)
