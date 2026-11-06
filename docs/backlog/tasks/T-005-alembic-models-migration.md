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
依 T-001 的 ERD 初始化 Alembic，建立 Sprint 1 所需的全部 SQLAlchemy model 與第一個 schema migration。

## 完成條件
- [ ] `alembic.ini` 與 `migrations/`：`env.py` 從 `app.core.config.Settings` 讀取 `DATABASE_URL`（不寫死），`target_metadata` 指向 `app.models` 的 `Base.metadata`；啟用 `render_as_batch=True`（SQLite 變更欄位需要）。
- [ ] `app/models/base.py`：`DeclarativeBase`、命名慣例（naming convention，讓 constraint 名稱可預測）、UTC timezone-aware datetime 型別（依 ADR-004）。
- [ ] Model（`Mapped` / `mapped_column` 寫法）：使用者、社團、社團負責人關聯、場地、不開放期間、借用申請、Session、登入失敗紀錄（依 ERD 實際命名）。
- [ ] 必要的 constraint 與 index：帳號唯一、外鍵、狀態與類型的 CHECK 白名單（申請狀態僅 `pending`、`approved`、`rejected`、`cancelled`，無「退回補件」）、`end_at > start_at` CHECK、借用申請 `(venue_id, start_at, end_at, status)` 查詢索引、不開放期間日期索引。
- [ ] 第一個 schema migration（不使用 `create_all()`）；`python -m alembic upgrade head` 與 `downgrade base` 皆可成功。
- [ ] `tests/conftest.py` 提供以 `alembic upgrade head` 建立暫存資料庫 schema 的 fixture。
- [ ] 測試：migration 可升降級；外鍵與 CHECK 生效（違反時拋出 IntegrityError）；`alembic check` 無 model 與 migration 差異。
- [ ] 更新 `docs/architecture/erd.md` 若實作與設計有差異（由 SA 確認）。

## 技術備註
- 可寫入：`app/models/`、`migrations/`、`alembic.ini`、`tests/`（fixture 與 model 測試）。
- Sprint 1 只有 DBA 撰寫 migration，T-006 接在本 Task 之後，避免 Alembic 多個 head。
- 時段重疊**無法**用 constraint 防止，由 T-018 以交易處理。

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
