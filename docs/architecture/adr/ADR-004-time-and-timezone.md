# ADR-004 時間與時區處理

- 狀態：Proposed（待 T-001 設計審查通過後改為 Accepted）
- 日期：2026-11-06（第 2 版：明定模組擁有者、`import datetime as dt`、migration 型別）
- 相關：US-004 AC1、AC8、AC11～AC13；US-002 AC1、AC5；US-017 AC2；T-003、T-005、T-014、T-016、T-019；AGENTS.md 1.3

## 背景

- AGENTS.md 1.3：時間一律以 UTC 儲存（timezone-aware `datetime`），顯示時轉換為 `Asia/Taipei`。
- 商業規則以**台灣當地日期**判斷：R-01（08:00–22:00）、不開放日（日曆日）、學期區間（月日）、R-13 工作天（「今天」與活動日都是當地日期）。
- 使用者決定（2026-11-06）：R-13 工作天＝**週一～週五**，不考慮國定假日與補班，不依賴不開放期間資料。
- SQLite 沒有 timezone-aware 的日期時間型別；SQLAlchemy `DateTime(timezone=True)` 在 SQLite 上會**靜默丟棄** tzinfo，讀回 naive datetime。
- ruff 已啟用 `DTZ` 規則（禁止 naive datetime）。

## 選項（SQLite 儲存格式）

| 選項 | 評估 |
|---|---|
| A. **`TypeDecorator` `UTCDateTime`：存成 naive UTC 字串，讀回附加 UTC** | SQLAlchemy SQLite `DateTime` 固定格式 `YYYY-MM-DD HH:MM:SS.ffffff`，定寬 → 字串排序＝時間排序，索引與區間比較正確；寫入 naive datetime 即拋錯，杜絕混用；DB 內容人類可讀 |
| B. 字串含時區位移（`+00:00` / `+08:00`） | 若混入不同位移，字串比較即錯誤；SQLAlchemy 預設不解析位移，需自訂格式 |
| C. Unix epoch 整數 | 排序正確，但 DB 不可讀、遷移與除錯成本高 |
| D. 直接用 `DateTime(timezone=True)` | tzinfo 被丟棄，讀回 naive，與 DTZ 規則衝突，容易出錯 |

## 決策

### 1. 儲存

- 時間點（`created_at`、`start_at`、`end_at`、`last_seen_at`、`locked_until`…）一律使用 `UTCDateTime`（**唯一定義位置 `app/models/base.py`，由 T-005 建立**；`app/core/db.py` 不定義）：

  ```python
  import datetime as dt

  import sqlalchemy as sa
  from sqlalchemy.engine import Dialect
  from sqlalchemy.types import TypeDecorator

  class UTCDateTime(TypeDecorator[dt.datetime]):
      """SQLite 用：寫入時要求 aware datetime 並轉 UTC 存成 naive 字串；讀出時附加 UTC。"""
      impl = sa.DateTime(timezone=False)
      cache_ok = True

      def process_bind_param(self, value: dt.datetime | None, dialect: Dialect) -> dt.datetime | None:
          if value is None:
              return None
          if value.tzinfo is None or value.utcoffset() is None:
              raise ValueError('UTCDateTime 不接受 naive datetime')
          return value.astimezone(dt.UTC).replace(tzinfo=None)

      def process_result_value(self, value: dt.datetime | None, dialect: Dialect) -> dt.datetime | None:
          return None if value is None else value.replace(tzinfo=dt.UTC)
  ```

- 日曆日（`closed_periods.start_date`/`end_date`、未來 `vacation_opening_rules`、`club_suspensions`）使用 `sa.Date`，語意為 `APP_TIMEZONE` 的當地日期，**不是**時間點，不做時區轉換。
- 時刻（未來固定保留的 `start_time`/`end_time`、寒暑假開放時段）使用 `sa.Time`，語意為當地時刻。
- 預設值由 Python 端 `dt.datetime.now(dt.UTC)` 產生（透過 `Clock` 或 model `default=`），不使用 SQLite `CURRENT_TIMESTAMP`。
- Migration 檔不匯入 `app.models`，`UTCDateTime` 欄位一律寫成 `sa.DateTime()`；`migrations/env.py` 以 `render_item` 讓 autogenerate 輸出 `sa.DateTime()`（erd.md 第 2 節）。

### 2. 時區與「今天」

- `APP_TIMEZONE`（預設 `Asia/Taipei`）同時用於**顯示**與**規則判斷**；以 `zoneinfo.ZoneInfo` 載入，`Settings` 啟動時驗證可載入。
- **跨平台**：Windows 沒有系統 IANA 時區資料庫，`zoneinfo` 需要 `tzdata` 套件 → **新增執行期相依 `tzdata`**（T-003 加入 `pyproject.toml`）。
- 「現在」只能從 `Clock.now_utc()` 取得；「今天」為 `Clock.today_local()` = `now_utc().astimezone(tz).date()`。service 與純函式**不得**自行呼叫 `dt.datetime.now()` / `dt.date.today()`（`date.today()` 依主機時區，違反規則）。

### 3. 轉換工具（`app/core/timeutils.py`，**T-003 建立**）

**`app/` 下所有模組**（models、schemas、repositories、services、routers、core、cli）與 `tests/` 一律 `import datetime as dt`，型別寫 `dt.date` / `dt.time` / `dt.datetime` / `dt.UTC`，不使用 `from datetime import ...`（避免 schema 欄位名 `date` 與型別同名；與 overview.md 2.1 同一規則）。

```python
def local_to_utc(day: dt.date, at: dt.time, tz: ZoneInfo) -> dt.datetime:
    """當地日期 + 時刻 → aware UTC。台灣無日光節約時間；以 dt.datetime.combine(day, at, tzinfo=tz) 實作。"""

def utc_to_local(moment: dt.datetime, tz: ZoneInfo) -> dt.datetime:
    """aware UTC → 當地 aware datetime（顯示用）。naive 輸入拋 ValueError。"""

def local_day_bounds_utc(start_day: dt.date, end_day: dt.date, tz: ZoneInfo) -> tuple[dt.datetime, dt.datetime]:
    """當地日期區間 [start_day, end_day]（含）→ UTC 半開區間 [start_day 00:00, end_day+1 00:00)。
    用於不開放期間受影響申請（T-013）與週檢視（T-016）查詢。"""
```

- 申請 22:00 結束：`local_to_utc(date, time(22, 0), tz)`，同一天內，不會跨日。
- 週檢視以 UTC 查出申請後轉回當地，依當地日期分組。

### 4. R-13 工作天（T-014 `app/services/workday.py`，純函式）

```python
REQUIRED_WORKDAYS: Final = 5

def is_workday(day: dt.date) -> bool:
    """週一～週五為 True（day.weekday() < 5）；不考慮國定假日與補班（使用者決定 2026-11-06）。"""

def latest_apply_date(event_date: dt.date, workdays: int = REQUIRED_WORKDAYS) -> dt.date:
    """由活動日往前推算第 workdays 個工作天（活動日本身不計）。workdays < 1 拋 ValueError。"""
    # d = event_date; count = 0
    # while count < workdays:
    #     d -= timedelta(days=1)
    #     if is_workday(d): count += 1
    # return d

def can_apply(today: dt.date, event_date: dt.date) -> bool:
    """today <= latest_apply_date(event_date)。today 由呼叫端以 Clock.today_local() 傳入。"""
```

- 不接受假日 / 不開放期間參數；不匯入 DB、設定或 `Clock`。
- 驗證範例：活動日 2026-11-16（一）→ 2026-11-09；2026-11-21（六）→ 2026-11-16；2026-11-23（一）→ 2026-11-16（其中 11/18 即使被設為國定假日型不開放日仍計入，US-004 AC13、US-017 AC2）；2027-01-04（一）→ 2026-12-28（跨年，2027-01-01（五）照算）。

### 5. 輸入格式

- 表單日期 `YYYY-MM-DD`（`<input type="date">`），時間 `HH:MM`（下拉選單）；Pydantic 解析為 `date` / `time`，**表單上的時間一律視為當地時間**。
- 秒與微秒必須為 0；分鐘必須為 0 或 30（US-004 AC9）。

## 影響

- 正面：DB 內時間可比較、可索引；naive datetime 在寫入時即被攔截；R-13 為純函式，可用參數化測試涵蓋所有 AC 範例。
- 負面：所有時間欄位必須使用 `UTCDateTime`，直接寫原生 SQL 比較時間需自行格式化（禁止，一律走 ORM）。
- 新增相依：`tzdata`（執行期）。
