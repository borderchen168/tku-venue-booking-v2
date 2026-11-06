---
id: T-005
title: Alembic 初始化與 Sprint 1 資料模型 migration
story: [US-013, US-001, US-017, US-002, US-004]
status: todo        # todo / in-progress / review / done / blocked
assignee: dba
branch: feature/T-005-alembic-models-migration
sprint: sprint-01
depends_on: [T-001, T-004]
created: 2026-11-06
---

# T-005 Alembic 初始化與 Sprint 1 資料模型 migration

## 說明
依 `docs/architecture/erd.md`（第 2 版）初始化 Alembic，建立 Sprint 1 所需的全部 SQLAlchemy model、列舉、`UTCDateTime` 型別與第一個 schema migration。
本 Task 是 `Base`、`NAMING_CONVENTION`、`UTCDateTime`、`TimestampMixin` 與 `app/models/enums.py` 的負責 Task（overview.md 3.1）。

## 完成條件
- [ ] `alembic.ini` 與 `migrations/`：`env.py` 從 `Settings` 讀取 `DATABASE_URL`（不寫死），`target_metadata` 指向 `Base.metadata`；`render_as_batch=True`；設定 `render_item` 讓 autogenerate 把 `UTCDateTime` 輸出為 `sa.DateTime()`，並讓 `compare_type` 視兩者相同（erd.md 第 2 節「Migration 中的型別」）。
- [ ] `app/models/base.py`：`Base`、`NAMING_CONVENTION`、**`UTCDateTime`**（ADR-004 第 1 節：naive 寫入拋 `ValueError`、讀出附 UTC）、`TimestampMixin`（ORM `default` / `onupdate`，不用 `server_default=func.now()`）。
- [ ] `app/models/enums.py`：`UserRole`、`VenueCategory`、`ClosedReasonType`、`BookingStatus`、`OCCUPYING_STATUSES`（overview.md 第 5 節）。
- [ ] Model（`user.py`、`club.py`、`venue.py`、`closed_period.py`、`booking.py`、`auth.py`）依 erd.md 第 3 節欄位、CHECK 名稱、index、外鍵 `ON DELETE` 行為，特別注意第 2 版變更：
  - `users` **不建** `email`、`must_change_password`；`clubs` **不建** `code`（列於 erd.md 第 4 節預留）。
  - `venues` 含 `sort_order`。
  - `user_sessions.user_id` 為 **NOT NULL**，**沒有** `authenticated_at` 欄位（只存已登入 Session）。
  - `login_throttles` 計數欄位為 **`attempt_count`**（CHECK `>= 0`），不對 `users` 設外鍵。
- [ ] `migrations/versions/0001_initial_schema.py`：**不匯入 `app.models`**，`UTCDateTime` 欄位寫 `sa.DateTime()`；不使用 `create_all()`；`upgrade head` 與 `downgrade base` 皆可成功。
- [ ] `tests/fixtures/` 提供以 `alembic upgrade head` 建立暫存資料庫 schema 的 `engine` fixture。
- [ ] 測試：migration 可升降級；外鍵與各具名 CHECK 生效（違反時 `IntegrityError`）；`UTCDateTime` 寫入 naive datetime 拋錯、讀回為 aware UTC；`alembic check` 無 model 與 migration 差異。
- [ ] 實作若需偏離 erd.md，先回報 SA 更新設計（DBA 不直接修改 `docs/architecture/`）。

## 技術備註
- 可寫入：`app/models/`、`migrations/`、`alembic.ini`、`tests/`（fixture 與 model 測試）。
- `app/models` 只能匯入 `app.models.*`（overview.md 第 2 節匯入規則）。
- Sprint 1 只有 DBA 撰寫 migration，T-006 接在本 Task 之後，避免 Alembic 多個 head。
- 時段重疊**無法**用 constraint 防止，由 T-018 以交易處理（ADR-003）。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（密碼欄位只存雜湊、Session 資料表設計）
- [ ] QA 驗收通過
- [ ] 文件與 .env.example 已更新
