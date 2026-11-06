# ADR-003 預約時段重疊檢查與寫入交易通則

- 狀態：Proposed（待 T-001 設計審查通過後改為 Accepted）
- 日期：2026-11-06（第 2 版：新增寫入交易通則、BUSY 判斷改用 primary code、前置條件精確化。第 3 版：通則改為「一致性關鍵判斷須在寫入交易內重讀」並列出例外、偵測 ORM bulk DML、禁止 text() 寫入）
- 相關：US-004 AC5～AC7；US-009 AC3、AC6、AC7（未來）；T-004、T-007、T-008、T-009、T-013、T-018、T-019、T-022；AGENTS.md 1.3
- 驗證環境：Code Reviewer 已於 Python 3.14.4 / SQLite 3.46.1 / SQLAlchemy 2.1.8 實測本 ADR 的交易行為

## 背景

同一場地的佔用申請（`pending`、`approved`）時段不可重疊。SQLite 沒有 exclusion constraint；若「先查詢、後寫入」不在同一個寫鎖交易內，兩個併發請求可能都查到「無衝突」（TOCTOU，CWE-367）。另外：

- pysqlite 預設的隱式交易會延後 `BEGIN`，使 `BEGIN IMMEDIATE` 無法直接控制。
- **WAL 模式下，deferred 交易「先讀後寫」在升級寫鎖時，若其他連線已在其快照之後寫入，會立即得到 `SQLITE_BUSY_SNAPSHOT`（extended code 517），不經 busy_timeout 等待**（Code Review 實測 0 秒失敗）。因此這不只是重疊檢查的問題，而是**所有寫入**的問題。

## 選項（重疊檢查）

| 選項 | 評估 |
|---|---|
| A. **`BEGIN IMMEDIATE` 交易內先 SELECT 衝突再 INSERT** | AGENTS.md 1.3 指定；IMMEDIATE 在交易開始即取得寫鎖，第二個寫入者在 `BEGIN IMMEDIATE` 就等待（busy_timeout），檢查與寫入之間不會有其他寫入 |
| B. DEFERRED 交易 + 樂觀檢查 | WAL 下讀後升級寫入會 `SQLITE_BUSY_SNAPSHOT`，需重試，不可靠 |
| C. 30 分鐘格子 + `UNIQUE(venue_id, slot_start)` | 每筆申請多列、狀態變更需同步、未來寒暑假與固定保留複雜 → 過度設計 |
| D. 應用程式內 `threading.Lock` | 多 worker / CLI 不共享 → 不正確 |

## 決策

採用 **A**，並訂定**寫入交易通則**（第 2.1 節）。

### 1. 區間語意

- 半開區間 `[start_at, end_at)`，皆為 UTC timezone-aware（ADR-004）。
- 重疊 ⇔ `existing.start_at < new.end_at AND existing.end_at > new.start_at`；相鄰不算重疊（US-004 AC6）。
- 佔用狀態：`OCCUPYING_STATUSES = frozenset({BookingStatus.PENDING, BookingStatus.APPROVED})`（`app/models/enums.py`）。`rejected`、`cancelled` 不佔用。
- 同一社團自己的佔用申請也算衝突。

### 2. 交易工具（T-004 `app/core/db.py`）

```python
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={
        'check_same_thread': False,                         # threadpool 中連線可能跨執行緒歸還連線池
        'timeout': settings.DATABASE_BUSY_TIMEOUT_MS / 1000, # SQLite busy handler；PRAGMA 不支援 bind parameter，故不用 PRAGMA busy_timeout
        # 注意：不可設定 'autocommit'（Python 3.12+ sqlite3 參數），會與下方 isolation_level=None 的作法衝突
    },
)

@event.listens_for(engine, 'connect')
def _on_connect(dbapi_conn: sqlite3.Connection, _record: object) -> None:
    dbapi_conn.isolation_level = None                      # 停用 pysqlite 隱式交易，改由 'begin' 事件發出 BEGIN
    cursor = dbapi_conn.cursor()
    cursor.execute('PRAGMA foreign_keys=ON')
    cursor.execute('PRAGMA journal_mode=WAL')
    cursor.close()

_BEGIN_STATEMENTS: Final = {'DEFERRED': 'BEGIN', 'IMMEDIATE': 'BEGIN IMMEDIATE'}

@event.listens_for(engine, 'begin')
def _on_begin(conn: Connection) -> None:
    mode = conn.get_execution_options().get('sqlite_begin_mode', 'DEFERRED')
    conn.exec_driver_sql(_BEGIN_STATEMENTS[mode])          # 白名單查表，非字串拼接

session_factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

@event.listens_for(session_factory, 'after_flush')
def _mark_flushed(session: Session, _ctx: object) -> None:
    session.info['has_writes'] = True

@event.listens_for(session_factory, 'do_orm_execute')
def _mark_orm_dml(state: ORMExecuteState) -> None:
    if state.is_insert or state.is_update or state.is_delete:   # ORM bulk / 條件式 DML（session.execute(update(...))）不經 flush
        state.session.info['has_writes'] = True

@event.listens_for(session_factory, 'after_transaction_end')
def _clear_flushed(session: Session, transaction: SessionTransaction) -> None:
    if transaction.parent is None:                         # 只在最外層交易結束時清除
        session.info.pop('has_writes', None)

@contextmanager
def immediate_transaction(session: Session) -> Iterator[Session]:
    """以 BEGIN IMMEDIATE 開啟交易；正常結束 commit，例外 rollback。

    前置條件：呼叫前目前交易內**沒有任何寫入**——包括 pending 物件（session.new / dirty / deleted 非空）、
    已 flush 但未 commit 的變更、以及 ORM DML 敘述（insert() / update() / delete()），後兩者由
    session.info['has_writes'] 追蹤（after_flush 與 do_orm_execute 事件）。違反時拋 RuntimeError（程式錯誤，及早發現）。
    以 text() 執行的寫入無法被偵測，因此**禁止以 text() 寫入**（見 2.1）。
    若 session 已有唯讀交易進行中，先 commit 結束它（expire_on_commit=False，已載入物件不失效），
    再以 session.connection(execution_options={'sqlite_begin_mode': 'IMMEDIATE'}) 開新交易（必須是新交易的第一個操作）。
    SQLite 寫鎖逾時轉為 ServiceBusyError（見 translate_busy_error）。
    """

def translate_busy_error(exc: sqlalchemy.exc.OperationalError) -> ServiceBusyError | None:
    """primary result code（低 8 位元）為 SQLITE_BUSY(5) 或 SQLITE_LOCKED(6) 時回傳 ServiceBusyError，否則 None。"""
    code = getattr(exc.orig, 'sqlite_errorcode', None)
    if code is not None and (code & 0xFF) in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}:
        return ServiceBusyError('系統忙碌，請稍後再試')
    return None
```

- BUSY 判斷必須以 `code & 0xFF` 取 primary code，涵蓋 extended code（例如 `SQLITE_BUSY_SNAPSHOT` = 517、`SQLITE_BUSY_RECOVERY` = 261、`SQLITE_LOCKED_SHAREDCACHE` = 262）（Code Review #2）。
- **靜默失效防護（Code Review #5）**：
  - `pyproject.toml`：`filterwarnings = ['error::sqlalchemy.exc.SAWarning']`，SQLAlchemy 對交易 / execution option 的警告直接使測試失敗。
  - T-004 以 `before_cursor_execute` 事件記錄送出的 SQL，斷言 `immediate_transaction` 內第一個敘述確實是 `BEGIN IMMEDIATE`、一般交易是 `BEGIN`。
  - 相依版本鎖定 `sqlalchemy>=2.0,<2.2`（overview.md 第 9 節），升級大版本前需重跑本 ADR 的測試。

### 2.1 寫入交易通則（Code Review #1）

> 1. **任何會寫入資料庫的交易，一律以 `immediate_transaction` 開始。** 唯讀查詢可使用預設 deferred 交易；唯讀交易之後要寫入時，由 `immediate_transaction` 結束唯讀交易並開新的寫入交易。
> 2. **一致性關鍵的判斷**——時段重疊、唯一性、計數 / 名額（例如 `login_throttles`）、以目前狀態為條件的狀態轉換——**必須在寫入交易內重新讀取並判斷**，不得沿用唯讀交易中讀到的值。
> 3. **例外**：已明確接受競態的商業規則檢查（R-01、不開放日、學期區間、R-13、權限、場地 / 社團啟用狀態）可以在寫入交易之前、以唯讀交易檢查，理由與影響見第 4 節（Code Review M-6）。
> 4. 寫入只能透過 ORM（unit of work 或 `insert()` / `update()` / `delete()`）；**禁止以 `text()` 執行 INSERT / UPDATE / DELETE**（`has_writes` 無法偵測，Code Review M-4）。`text()` 僅可用於帶 bind parameter 的唯讀查詢。
> 5. 以讀到的舊值為前提的更新，使用條件式 UPDATE（例如 `WHERE password_hash = :old`、未來狀態轉換的 `WHERE status = :expected`），並檢查影響列數。

各元件交易方式：

| 元件 | 操作 | 交易方式 | Task |
|---|---|---|---|
| `ServerSessionMiddleware` / `SessionStore` | 讀取 Session | 自有 DB Session，唯讀 deferred，讀完即關 | T-007 |
| 同上 | 刪除失效列、更新 `last_seen_at` | 自有 DB Session，`immediate_transaction` | T-007 |
| `create_session_for_user`、`destroy_session`、`add_flash`、`pop_flashes`、`delete_for_user`、`delete_expired` | 寫入 `user_sessions` | 各自 `immediate_transaction`（自有 DB Session） | T-007 |
| `AuthService` / `LoginThrottleRepository` | `reserve_attempt`（讀取＋遞增＋可能鎖定） | `immediate_transaction`，**在 argon2 驗證之前 commit**（ADR-005） | T-008 |
| 同上 | 成功登入：刪除 throttle 列、needs_rehash 時以 `WHERE id = :id AND password_hash = :old` 條件式更新 | 同一個 `immediate_transaction` | T-008 |
| 同上 | `maybe_cleanup`：`delete_expired` 與 `delete_stale`（`reserve_attempt` 之後依間隔觸發） | 各自另開 `immediate_transaction` | T-008 |
| `AccountService`（CLI） | 唯一性檢查＋建立使用者 / 社團 / 負責人、`unlock_user` | 單一 `immediate_transaction`（檢查與寫入同一交易） | T-009 |
| `ClosedPeriodService` | `create` / `update` / `delete` | `immediate_transaction`；`create` 的受影響申請清單在同一交易內查詢 | T-013 |
| `BookingRepository.create_if_no_overlap` | 重疊檢查＋INSERT | `immediate_transaction` | T-018 |
| `BookingService.apply` | 規則檢查（唯讀）→ `create_if_no_overlap` | 通則第 3 點的例外：商業規則在請求 Session 的唯讀交易中檢查（競態依第 4 節接受）；重疊（一致性關鍵）在 `create_if_no_overlap` 的寫入交易內重讀 | T-019 |
| Venue / Availability / 頁面查詢 | 純讀取 | 預設 deferred | T-011、T-016 |

- 請求層 `get_session()`：yield 一個 Session，請求結束時 `close()`（未 commit 的唯讀交易隨之 rollback）；不在 dependency 中自動 commit。

### 3. Repository（T-018 `app/repositories/booking_repository.py`）

```python
@dataclass(frozen=True, slots=True)
class NewBookingApplication:
    venue_id: int
    club_id: int
    applicant_id: int
    start_at: dt.datetime            # aware UTC
    end_at: dt.datetime              # aware UTC
    activity_name: str
    activity_description: str
    expected_attendees: int

class BookingRepository:
    def __init__(self, session: Session) -> None: ...

    def find_overlapping(self, venue_id: int, start_at: dt.datetime, end_at: dt.datetime) -> list[BookingApplication]:
        """回傳與 [start_at, end_at) 重疊的佔用申請（status ∈ OCCUPYING_STATUSES）。"""
        # select(BookingApplication).where(
        #     BookingApplication.venue_id == venue_id,
        #     BookingApplication.status.in_(OCCUPYING_STATUSES),
        #     BookingApplication.start_at < end_at,
        #     BookingApplication.end_at > start_at,
        # ).order_by(BookingApplication.start_at)

    def create_if_no_overlap(self, new: NewBookingApplication) -> BookingApplication:
        """在 immediate_transaction 中檢查衝突並建立 status='pending' 的申請。

        Raises:
            BookingConflictError: 有重疊的佔用申請。
            ServiceBusyError: 等待寫鎖逾時。
        """
        # with immediate_transaction(self._session):
        #     if self.find_overlapping(new.venue_id, new.start_at, new.end_at):
        #         raise BookingConflictError('該時段已被借用')
        #     entity = BookingApplication(..., status=BookingStatus.PENDING)
        #     self._session.add(entity)
        #     self._session.flush()       # 取得 id
        # return entity

    def list_occupying_between(self, start_at: dt.datetime, end_at: dt.datetime, venue_id: int | None = None) -> list[BookingApplication]:
        """T-013 受影響申請（venue_id=None 表示全部場地）、T-016 週檢視共用。"""
```

- 參數一律經 ORM bind，`UTCDateTime` 確保比較值與儲存格式一致。不得使用 `func.now()` / `CURRENT_TIMESTAMP` 參與比較。
- **衝突查詢集中在本 repository**；T-019 只呼叫 `create_if_no_overlap`，未來擴充固定保留時段不需修改 T-019。
- 商業規則（R-01、不開放日、學期、R-13、權限）由 T-019 在呼叫前檢查，不放進寫鎖交易。

### 4. 已知可接受的競態（通則第 3 點的例外清單）

| 規則 | 競態情境 | 影響與處理 |
|---|---|---|
| 不開放日（R-03～R-05） | 承辦人新增不開放期間與學生送出申請同時發生，申請在期間建立後才寫入 | US-017 AC3 受影響清單會列出該申請，承辦人以 US-012 處理 |
| 場地 / 社團啟用、社團負責人資格 | 停用或移除負責人與申請同時發生 | 申請以「審核中」建立，承辦人審核（US-006）時可駁回 |
| R-01、學期區間、R-13 | 由程式常數與 `today` 決定，不依賴 DB 中會被併發修改的資料 | 無實際競態 |

以上規則若日後改為一致性關鍵（例如停權需即時生效），須移入寫入交易內重讀。

### 5. 未來擴充：固定保留時段（US-009，Sprint 1 不實作）

資料模型見 ADR-006。屆時 `create_if_no_overlap` 在**同一個** `BEGIN IMMEDIATE` 交易內多查一張表：

```text
衝突 = 佔用申請重疊（任何社團）
     ∪ fixed_reservation_occurrences 重疊
         且 status = 'reserved'
         且 club_id ≠ new.club_id          ← 自己社團的保留時段不算衝突（US-009 AC6）
```

- 若新申請完全落在自己社團某個保留場次內，service 將 `fixed_reservation_occurrence_id` 填入申請。
- US-009 登錄保留時段時反向檢查：與**其他社團**的佔用申請或任何保留場次重疊 → 整批不建立（US-009 AC3），同樣在 `BEGIN IMMEDIATE` 內完成。
- `find_overlapping` 屆時改回傳 `list[Conflict]`（含來源類型），只影響 repository 與其測試。

### 6. 測試策略

| 類型 | 內容 | Task |
|---|---|---|
| 交易工具 | `BEGIN` / `BEGIN IMMEDIATE` 確實送出（`before_cursor_execute`）；例外時 rollback；前置條件：有 pending 物件、已 flush 未 commit、或已執行 ORM bulk DML（`session.execute(update(...))`、`session.execute(delete(...))`、`session.execute(insert(...))`）時呼叫 → `RuntimeError`；`has_writes` 在 commit / rollback 後清除；唯讀交易進行中呼叫 → 正常；兩連線同時 `BEGIN IMMEDIATE` 第二個等待 / 逾時 | T-004 |
| BUSY 轉換 | 以假的 `OperationalError`（`sqlite_errorcode` = 5、6、517、261、262）→ `ServiceBusyError`；其他錯誤碼（例如 19 constraint）→ 原樣拋出；再以真實雙連線情境產生 `SQLITE_BUSY` 驗證 | T-004 |
| WAL 回歸 | 證明通則必要性：deferred 交易先讀、另一連線寫入並 commit、原交易再寫 → 得到 extended code 517；同情境改用 `immediate_transaction` → 正常等待後成功 | T-004 |
| 重疊規則 | AC5：既有 18:00–20:00，新 19:00–21:00、17:00–18:30、18:00–20:00 → `BookingConflictError`；既有為 `rejected` / `cancelled` → 成功；AC6：20:00–22:00 → 成功；不同場地同時段 → 成功 | T-018 |
| 確定性鎖測試 | 連線 A 開 `immediate_transaction` 不結束；連線 B（timeout 0.1 秒）呼叫 `create_if_no_overlap` → `ServiceBusyError`；A 寫入同時段並 commit 後，B 重試 → `BookingConflictError` | T-018 |
| 併發 | 同一 `tmp_path` SQLite 檔、`threading.Barrier(8)`、8 個執行緒各自 `session_factory()`，同時 `create_if_no_overlap` 同一時段；恰 1 成功、7 個 `BookingConflictError`、0 個 `ServiceBusyError`；`pytest.mark.parametrize('round_', range(20))` 重複 20 輪 | T-018 |
| 不變量 | 測試結束以自我 JOIN 斷言同場地不存在任何一對重疊的佔用申請 | T-018 |
| HTTP 併發 | 兩位不同學生各自 `TestClient`（各自 Cookie）在兩個執行緒同時 `POST /bookings` 同一時段，恰一個 303、一個 409 | T-022 |

## 影響

- 正面：符合 AGENTS.md 1.3；併發下保證不重疊；所有寫入行為一致，避免 WAL 快照升級失敗。
- 負面：所有寫入在 SQLite 層序列化（寫入量低，可接受）；開發者須遵守通則（以 `RuntimeError`、`SAWarning`→error、`before_cursor_execute` 測試及早發現）。
- 新設定：`DATABASE_BUSY_TIMEOUT_MS`；相依版本 `sqlalchemy>=2.0,<2.2`。
