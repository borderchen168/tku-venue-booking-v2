"""「現在時間」的唯一來源（overview.md 2.1、ADR-004 第 2 節）。

service 與純函式不得自行呼叫 `dt.datetime.now()` / `dt.date.today()`；route 以 `Depends(get_clock)` 取得 Clock，
測試以 `app.dependency_overrides[get_clock]` 換成 `tests/fixtures/clock.py` 的 `FixedClock`。
"""

import datetime as dt
from typing import Annotated, Protocol
from zoneinfo import ZoneInfo

from fastapi import Depends

from app.core.config import Settings, get_settings


class Clock(Protocol):
    """時鐘介面。"""

    def now_utc(self) -> dt.datetime:
        """目前時間（timezone-aware UTC）。"""
        ...

    def today_local(self) -> dt.date:
        """`APP_TIMEZONE` 的今天日期。"""
        ...


class SystemClock:
    """以系統時間實作的 Clock（預設）。"""

    def __init__(self, tz: ZoneInfo) -> None:
        self._tz = tz

    def now_utc(self) -> dt.datetime:
        """目前時間（timezone-aware UTC）。"""
        return dt.datetime.now(dt.UTC)

    def today_local(self) -> dt.date:
        """`APP_TIMEZONE` 的今天日期（不依主機時區）。"""
        return self.now_utc().astimezone(self._tz).date()


def get_clock(settings: Annotated[Settings, Depends(get_settings)]) -> Clock:
    """FastAPI 相依：回傳依 `APP_TIMEZONE` 建立的 `SystemClock`。"""
    return SystemClock(settings.tz)
