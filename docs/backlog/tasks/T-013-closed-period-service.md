---
id: T-013
title: 不開放期間 service
story: US-017
status: todo        # todo / in-progress / review / done / blocked
assignee: backend-developer
branch: feature/T-013-closed-period-service
sprint: sprint-01
depends_on: [T-005, T-008]
created: 2026-11-06
---

# T-013 不開放期間 service

## 說明
實作不開放日期 / 期間的新增、查詢、編輯、刪除，以及供借用狀況（US-002）與申請檢查（US-004，R-03～R-05 不開放日期）使用的查詢介面。R-13 工作天計算只算週一～週五，**不使用**本 Task 的資料（使用者決定）。

## 完成條件
- [ ] `app/schemas/closed_period.py`：起日、迄日（ISO 日期）、類型列舉白名單（國定假日／考試週／大型考試／其他）、說明 1～100 字；驗證起日 ≤ 迄日、期間 ≤ 366 天（US-017 AC5）。
- [ ] `app/repositories/closed_period_repository.py`、`app/services/closed_period_service.py`：
  - 建立 / 更新 / 刪除，限 `staff`（service 層檢查角色，預設拒絕，US-017 AC6）。
  - 建立後回傳期間內狀態為審核中（`pending`）、已核准（`approved`）的受影響申請清單（AC3），不自動取消。
  - 查詢：指定日期區間內的不開放期間（供 T-016）、指定日期是否不開放及原因類型（供 T-019）。
- [ ] 安全日誌：新增、修改、刪除事件（操作者 user id、期間 id）。
- [ ] 單元測試：欄位驗證邊界（同一天、366/367 天、說明 0/1/100/101 字）、非 staff 被拒、受影響申請查詢只含佔用狀態（`pending`、`approved`）。

## 技術備註
- 類型「國定假日」僅代表該日場地不開放借用，不影響 R-13 工作天計算。
- 第一版不開放期間適用全部場地、整天不開放（US-017 假設）。
- AC3 受影響清單中的「取消連結」依賴 US-012（不在 Sprint 1），本 Sprint 只顯示清單。

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
