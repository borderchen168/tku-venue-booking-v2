---
id: T-004
title: DB 連線、PRAGMA 與交易工具
story: [US-013, US-001, US-017, US-002, US-004]
status: todo        # todo / in-progress / review / done / blocked
assignee: backend-developer
branch: feature/T-004-db-connection-transaction
sprint: sprint-01
depends_on: [T-003]
created: 2026-11-06
---

# T-004 DB 連線、PRAGMA 與交易工具

## 說明
依 ADR-003（第 3 版）第 2、2.1 節建立 SQLAlchemy 2.0 同步 engine 與 Session 管理，確保每個連線啟用 `PRAGMA foreign_keys=ON` 與 `journal_mode=WAL`，
並提供 `immediate_transaction` 與 `translate_busy_error`。依 ADR-003 寫入交易通則，**所有寫入交易都以 `immediate_transaction` 開始**，
本 Task 的工具與測試是 T-007、T-008、T-009、T-013、T-018、T-019 的共同基礎。

## 完成條件
- [ ] `app/core/db.py`：`engine`、`session_factory`、`get_session`、`immediate_transaction`、`translate_busy_error` 依 ADR-003 第 2 節程式骨架實作（overview.md 3.1）：
  - busy timeout 以 `connect_args={'timeout': DATABASE_BUSY_TIMEOUT_MS / 1000}` 設定（**不用** `PRAGMA busy_timeout`）；`check_same_thread=False`；不設定 `autocommit` 參數。
  - `connect` 事件設 `isolation_level = None` 並執行 `PRAGMA foreign_keys=ON`、`PRAGMA journal_mode=WAL`；`begin` 事件依 execution option `sqlite_begin_mode` 以白名單發出 `BEGIN` / `BEGIN IMMEDIATE`。
  - `immediate_transaction` **前置條件檢查**：`session.new` / `dirty` / `deleted` 非空，或 `session.info['has_writes']` 為真時拋 `RuntimeError`；已有唯讀交易時先 commit 再開新交易。
  - `has_writes` 以三個 `session_factory` 事件維護（ADR-003 第 2 節程式骨架）：`after_flush`（unit of work 寫入）、**`do_orm_execute`（`state.is_insert / is_update / is_delete`，涵蓋不經 flush 的 ORM bulk / 條件式 DML，例如 `session.execute(update(...))`）**、`after_transaction_end`（只在最外層交易結束時清除）。
  - `translate_busy_error` 以 **primary code**（`sqlite_errorcode & 0xFF`）判斷 `SQLITE_BUSY` / `SQLITE_LOCKED`，轉為 T-003 的 `ServiceBusyError`。
  - `get_session()` 請求結束時 `close()`，不自動 commit（ADR-003 2.1）。
- [ ] SQLite 檔案所在目錄不存在時自動建立（`pathlib.Path`）。
- [ ] `tests/fixtures/`：每個測試使用 `tmp_path` 下獨立的 SQLite 檔案與 engine fixture，不使用開發用資料庫。
- [ ] 測試（ADR-003 第 6 節「交易工具」「BUSY 轉換」「WAL 回歸」三列全部項目）：
  - 新連線 `foreign_keys` 為 1、`journal_mode` 為 `wal`。
  - 以 `before_cursor_execute` 事件記錄 SQL，斷言 `immediate_transaction` 內第一個敘述為 `BEGIN IMMEDIATE`、一般交易為 `BEGIN`。
  - 例外時 rollback；有 pending 物件、或已 flush 未 commit 時呼叫 → `RuntimeError`；**已執行 ORM bulk DML（`session.execute(insert(...) / update(...) / delete(...))`）未 commit 時呼叫 → `RuntimeError`**；唯讀交易進行中呼叫 → 正常；交易結束（commit / rollback）後 `has_writes` 被清除，可再次呼叫。
  - 兩連線同時 `BEGIN IMMEDIATE`，第二個等待 / 逾時。
  - `translate_busy_error`：`sqlite_errorcode` 為 5、6、517、261、262 → `ServiceBusyError`；19 等其他碼 → `None`；另以真實雙連線情境產生 BUSY 驗證。
  - **WAL 517 回歸測試**：deferred 交易先讀、另一連線寫入並 commit、原交易再寫 → extended code 517；同情境改用 `immediate_transaction` → 等待後成功。

## 技術備註
- **`UTCDateTime` 不在本 Task 定義**，由 T-005 建立於 `app/models/base.py`（ADR-004 第 1 節、overview.md 3.1）；本 Task 不定義任何 model。
- router 不直接操作 Session（分層原則），`get_session()` 僅供 `routers/deps.py` 的 service 工廠使用（overview.md 2.1）。
- **禁止以 `text()` 執行 INSERT / UPDATE / DELETE**（`has_writes` 無法偵測，ADR-003 2.1 第 4 點）；`text()` 僅可用於帶 bind parameter 的唯讀查詢。`BEGIN` 敘述以白名單查表產生，非字串拼接。
- 以讀到的舊值為前提的更新一律用條件式 UPDATE 並檢查影響列數（ADR-003 2.1 第 5 點）；本 Task 在 `immediate_transaction` docstring 中引用此通則，供 T-007、T-008、T-009、T-013、T-018 遵循。
- 驗證環境見 ADR-003 開頭（Python 3.14.4 / SQLite 3.46.1 / SQLAlchemy 2.1.8）；若行為不同請回報 SA。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（如適用）
- [ ] QA 驗收通過
- [ ] 文件與 .env.example 已更新
