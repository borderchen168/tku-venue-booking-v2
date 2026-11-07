"""時區轉換工具（ADR-004 第 3 節）。

DB 只存 timezone-aware UTC；`dt.date` 代表 `APP_TIMEZONE` 的日曆日，`dt.time` 代表當地時刻。
"""

import datetime as dt
from zoneinfo import ZoneInfo


def _require_aware(moment: dt.datetime) -> None:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError('不接受 naive datetime')


def local_to_utc(day: dt.date, at: dt.time, tz: ZoneInfo) -> dt.datetime:
    """當地日期 + 時刻 → aware UTC。台灣無日光節約時間；以 dt.datetime.combine(day, at, tzinfo=tz) 實作。

    Raises:
        ValueError: `at` 已帶 tzinfo（當地時刻必須是 naive time，避免混用時區）。
    """
    if at.tzinfo is not None:
        raise ValueError('當地時刻不可帶 tzinfo')
    return dt.datetime.combine(day, at, tzinfo=tz).astimezone(dt.UTC)


def utc_to_local(moment: dt.datetime, tz: ZoneInfo) -> dt.datetime:
    """aware UTC → 當地 aware datetime（顯示用）。naive 輸入拋 ValueError。"""
    _require_aware(moment)
    return moment.astimezone(tz)


def local_day_bounds_utc(start_day: dt.date, end_day: dt.date, tz: ZoneInfo) -> tuple[dt.datetime, dt.datetime]:
    """當地日期區間 [start_day, end_day]（含）→ UTC 半開區間 [start_day 00:00, end_day+1 00:00)。

    用於不開放期間受影響申請（T-013）與週檢視（T-016）查詢。

    Raises:
        ValueError: `end_day` 早於 `start_day`。
    """
    if end_day < start_day:
        raise ValueError('end_day 不可早於 start_day')
    start = local_to_utc(start_day, dt.time(0, 0), tz)
    end = local_to_utc(end_day + dt.timedelta(days=1), dt.time(0, 0), tz)
    return start, end
