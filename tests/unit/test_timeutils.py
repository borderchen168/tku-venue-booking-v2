"""時間轉換工具測試（ADR-004 第 3 節）。"""

import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from app.core.timeutils import local_day_bounds_utc, local_to_utc, utc_to_local

TAIPEI = ZoneInfo('Asia/Taipei')
# 刻意移除 tzinfo 的 naive datetime，用於驗證拒絕 naive 輸入
NAIVE = dt.datetime(2026, 11, 9, 2, 0, tzinfo=dt.UTC).replace(tzinfo=None)


def test_local_to_utc() -> None:
    result = local_to_utc(dt.date(2026, 11, 16), dt.time(8, 0), TAIPEI)
    assert result == dt.datetime(2026, 11, 16, 0, 0, tzinfo=dt.UTC)
    assert result.tzinfo is dt.UTC


def test_local_to_utc_end_of_day_same_date() -> None:
    assert local_to_utc(dt.date(2026, 11, 16), dt.time(22, 0), TAIPEI) == dt.datetime(2026, 11, 16, 14, 0, tzinfo=dt.UTC)


def test_local_midnight_is_previous_utc_day() -> None:
    assert local_to_utc(dt.date(2026, 11, 16), dt.time(0, 0), TAIPEI) == dt.datetime(2026, 11, 15, 16, 0, tzinfo=dt.UTC)


def test_local_to_utc_rejects_aware_time() -> None:
    with pytest.raises(ValueError, match='tzinfo'):
        local_to_utc(dt.date(2026, 11, 16), dt.time(8, 0, tzinfo=dt.UTC), TAIPEI)


def test_utc_to_local() -> None:
    result = utc_to_local(dt.datetime(2026, 11, 15, 16, 30, tzinfo=dt.UTC), TAIPEI)
    assert result == dt.datetime(2026, 11, 16, 0, 30, tzinfo=TAIPEI)
    assert result.date() == dt.date(2026, 11, 16)
    assert result.utcoffset() == dt.timedelta(hours=8)


def test_utc_to_local_rejects_naive() -> None:
    with pytest.raises(ValueError, match='naive'):
        utc_to_local(NAIVE, TAIPEI)


def test_utc_to_local_accepts_other_aware_offset() -> None:
    moment = dt.datetime(2026, 11, 16, 9, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))
    assert utc_to_local(moment, TAIPEI).hour == 8


def test_roundtrip() -> None:
    moment = local_to_utc(dt.date(2026, 12, 31), dt.time(23, 30), TAIPEI)
    local = utc_to_local(moment, TAIPEI)
    assert (local.date(), local.time()) == (dt.date(2026, 12, 31), dt.time(23, 30))


def test_local_day_bounds_single_day() -> None:
    start, end = local_day_bounds_utc(dt.date(2026, 11, 16), dt.date(2026, 11, 16), TAIPEI)
    assert start == dt.datetime(2026, 11, 15, 16, 0, tzinfo=dt.UTC)
    assert end == dt.datetime(2026, 11, 16, 16, 0, tzinfo=dt.UTC)


def test_local_day_bounds_week_across_year() -> None:
    start, end = local_day_bounds_utc(dt.date(2026, 12, 28), dt.date(2027, 1, 3), TAIPEI)
    assert start == dt.datetime(2026, 12, 27, 16, 0, tzinfo=dt.UTC)
    assert end == dt.datetime(2027, 1, 3, 16, 0, tzinfo=dt.UTC)
    # 半開區間：end_day 22:00 在區間內、隔天 00:00 不在
    assert start <= local_to_utc(dt.date(2027, 1, 3), dt.time(22, 0), TAIPEI) < end
    assert not local_to_utc(dt.date(2027, 1, 4), dt.time(0, 0), TAIPEI) < end


def test_local_day_bounds_rejects_reversed_range() -> None:
    with pytest.raises(ValueError, match='end_day'):
        local_day_bounds_utc(dt.date(2026, 11, 17), dt.date(2026, 11, 16), TAIPEI)
