"""Clock 測試（overview.md 2.1、ADR-004 第 2 節）。"""

import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app.core.clock import Clock, SystemClock, get_clock
from tests.fixtures.clock import FixedClock
from tests.fixtures.settings import make_settings

TAIPEI = ZoneInfo('Asia/Taipei')
# 刻意移除 tzinfo 的 naive datetime，用於驗證拒絕 naive 輸入
NAIVE = dt.datetime(2026, 11, 9, 2, 0, tzinfo=dt.UTC).replace(tzinfo=None)


def test_system_clock_now_is_aware_utc() -> None:
    now = SystemClock(TAIPEI).now_utc()
    assert now.tzinfo is dt.UTC
    assert abs(now - dt.datetime.now(dt.UTC)) < dt.timedelta(seconds=5)


# UTC 2026-11-09 16:30：台北已是 11-10，UTC 仍是 11-09，Kiritimati（UTC+14）是 11-10 06:30
LATE_UTC = dt.datetime(2026, 11, 9, 16, 30, tzinfo=dt.UTC)


@pytest.fixture
def frozen_system_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """固定 SystemClock.now_utc，避免測試剛好跨午夜時偶發失敗。"""
    monkeypatch.setattr(SystemClock, 'now_utc', lambda self: LATE_UTC)


@pytest.mark.usefixtures('frozen_system_time')
def test_system_clock_today_uses_configured_timezone() -> None:
    assert SystemClock(TAIPEI).today_local() == dt.date(2026, 11, 10)
    assert SystemClock(ZoneInfo('UTC')).today_local() == dt.date(2026, 11, 9)


@pytest.mark.usefixtures('frozen_system_time')
def test_get_clock_uses_settings_timezone(tmp_path: Path) -> None:
    clock = get_clock(make_settings(tmp_path, APP_TIMEZONE='America/Los_Angeles'))
    assert isinstance(clock, SystemClock)
    assert clock.today_local() == dt.date(2026, 11, 9)
    assert get_clock(make_settings(tmp_path, APP_TIMEZONE='Pacific/Kiritimati')).today_local() == dt.date(2026, 11, 10)


def test_fixed_clock_local_date_crosses_midnight() -> None:
    # UTC 2026-11-09 16:30 = 台北 2026-11-10 00:30
    clock: Clock = FixedClock(dt.datetime(2026, 11, 9, 16, 30, tzinfo=dt.UTC), TAIPEI)
    assert clock.today_local() == dt.date(2026, 11, 10)
    assert clock.now_utc() == dt.datetime(2026, 11, 9, 16, 30, tzinfo=dt.UTC)


def test_fixed_clock_rejects_naive() -> None:
    with pytest.raises(ValueError, match='naive'):
        FixedClock(NAIVE, TAIPEI)


def test_fixed_clock_normalizes_to_utc_and_advances(fixed_clock: FixedClock) -> None:
    fixed_clock.set_now(dt.datetime(2026, 11, 9, 23, 59, tzinfo=TAIPEI))
    assert fixed_clock.now_utc().tzinfo is dt.UTC
    assert fixed_clock.today_local() == dt.date(2026, 11, 9)
    fixed_clock.advance(dt.timedelta(minutes=1))
    assert fixed_clock.today_local() == dt.date(2026, 11, 10)


def test_fixed_clock_fixture_default(fixed_clock: FixedClock) -> None:
    assert fixed_clock.today_local() == dt.date(2026, 11, 9)
    assert fixed_clock.today_local().weekday() == 0
