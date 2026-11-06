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
建立 SQLAlchemy 2.0 同步 engine 與 Session 管理，確保每個連線啟用 `PRAGMA foreign_keys=ON` 與 `journal_mode=WAL`，
並提供 `BEGIN IMMEDIATE` 交易工具，作為 US-004 時段重疊檢查（AGENTS.md 1.3）的基礎。

## 完成條件
- [ ] `app/core/db.py`：依 `Settings.DATABASE_URL` 建立 engine；以 `connect` 事件對每個連線執行 `PRAGMA foreign_keys=ON`、`PRAGMA journal_mode=WAL`，並設定合理的 `busy_timeout`。
- [ ] 停用 pysqlite 預設的隱式交易行為，使 `BEGIN IMMEDIATE` 可由程式明確控制（依 SQLAlchemy 官方 SQLite 文件的作法）。
- [ ] 提供 FastAPI 相依函式 `get_session()`（請求結束時關閉）與 `immediate_transaction(session)` context manager（`BEGIN IMMEDIATE` → commit / rollback）。
- [ ] SQLite 檔案所在目錄不存在時自動建立（`pathlib.Path`）。
- [ ] `tests/conftest.py`：每個測試使用 `tmp_path` 下獨立的 SQLite 檔案與 engine fixture，不使用開發用資料庫。
- [ ] 測試：新連線的 `foreign_keys` 為 1、`journal_mode` 為 `wal`；`immediate_transaction` 例外時 rollback；兩個連線同時 `BEGIN IMMEDIATE` 時第二個需等待或逾時（驗證寫鎖行為）。

## 技術備註
- `DeclarativeBase` 與 model 由 DBA 於 T-005 放在 `app/models/`，本 Task 不定義 model。
- router 不直接操作 Session（分層原則），`get_session()` 僅供 service / repository 相依注入使用。
- `text()` 若有使用，一律 bind parameter。

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
