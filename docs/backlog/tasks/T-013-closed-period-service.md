---
id: T-013
title: 不開放期間 service
story: US-017
status: todo        # todo / in-progress / review / done / blocked
assignee: backend-developer
branch: feature/T-013-closed-period-service
sprint: sprint-01
depends_on: [T-005, T-008, T-018]
created: 2026-11-06
---

# T-013 不開放期間 service

## 說明
依 routes.md 2.4「Service 介面」實作不開放日期 / 期間的新增、查詢、編輯、刪除，以及供借用狀況（US-002）與申請檢查（US-004，R-03～R-05 不開放日期）使用的內部查詢介面。
R-13 工作天計算只算週一～週五，**不使用**本 Task 的資料（使用者決定，ADR-004 第 4 節）。

## 完成條件
- [ ] `app/schemas/closed_period.py`：`ClosedPeriodInput`（起日 ≤ 迄日、`(end - start).days <= 365`、`reason_type` 白名單、說明 1～100 字，US-017 AC5）、`ClosedPeriodOut`、`AffectedApplication`、`ClosedPeriodDetail`（routes.md 2.4）；Pydantic 錯誤以 `to_field_errors`（T-003）轉為逐欄訊息。
- [ ] `app/repositories/closed_period_repository.py`、`app/services/closed_period_service.py` `ClosedPeriodService`，方法簽章依 routes.md 2.4：
  - `list_periods` / `get_period` / `create` / `update` / `delete`：actor 必須為 `staff`，否則拋 `PermissionDeniedError(reason='role_required:staff')`（預設拒絕，US-017 AC6；`access.denied` 由全域 handler 記錄，service 不寫日誌）；不存在 → `NotFoundError`。
  - **`create` 回傳 `ClosedPeriodDetail`**（含期間內 `pending` / `approved` 受影響申請與 `affected_count`，AC3），受影響清單與 INSERT 在同一交易內查詢；不自動取消。
  - **所有寫入（`create` / `update` / `delete`）一律 `immediate_transaction`**（ADR-003 2.1）。
  - 內部查詢 `closures_between(start, end)`、`closures_on(day)`（無 actor，供 T-016、T-019，回傳不含個資）；涵蓋同一日的多個期間回傳去重後的原因類型（erd.md 3.5）。
  - 受影響申請以 `local_day_bounds_utc`（T-003 `app/core/timeutils.py`）換算 UTC 區間，並透過 T-018 的 `BookingRepository.list_occupying_between` 查詢。
- [ ] 安全日誌：`closed_period.created`（含 `affected_count`）、`closed_period.updated`、`closed_period.deleted`，欄位依 security-logging.md 第 2 節（不記錄 `description`）。
- [ ] 單元測試：欄位驗證邊界（同一天、跨 366 天（差 365）可、差 366 不可、說明 0/1/100/101 字）、非 staff 被拒、受影響申請只含佔用狀態且依當地日界判斷、`create` 回傳 `ClosedPeriodDetail`、重疊期間的原因類型去重、寫入確實以 `BEGIN IMMEDIATE` 開始（可沿用 T-004 的 SQL 記錄 fixture）、安全日誌欄位。

## 技術備註
- 類型「國定假日」僅代表該日場地不開放借用，不影響 R-13 工作天計算（US-017 AC2）。
- 第一版不開放期間適用全部場地、整天不開放（US-017 假設）。
- AC3 受影響清單中的「取消連結」依賴 US-012（不在 Sprint 1），本 Sprint 只顯示清單。
- 新增相依 T-018：受影響申請查詢使用 `booking_repository.list_occupying_between`（overview.md 3.2、ADR-003 第 3 節），衝突 / 佔用查詢集中在該 repository。
- 新增期間與學生送出申請恰好同時發生的競態屬已知可接受風險（ADR-003 第 4 節）。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（存取控制、輸入驗證）
- [ ] QA 驗收通過
- [ ] 文件與 .env.example 已更新
