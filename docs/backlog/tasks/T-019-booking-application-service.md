---
id: T-019
title: 借用申請 service（規則驗證、授權、日誌）
story: US-004
status: todo        # todo / in-progress / review / done / blocked
assignee: backend-developer
branch: feature/T-019-booking-application-service
sprint: sprint-01
depends_on: [T-008, T-009, T-011, T-013, T-014, T-018]
created: 2026-11-06
---

# T-019 借用申請 service（規則驗證、授權、日誌）

## 說明
整合場地（T-011）、社團負責人（T-009 `club_repository`）、不開放期間（R-03～R-05，T-013）、學期區間與工作天（T-014 純函式）與重疊檢查（T-018），
實作學生以社團名義申請臨時借用的商業邏輯（US-004），以及申請人查看自己申請的查詢。檢查順序以 overview.md 第 6 節流程圖為準。

## 完成條件
- [ ] `app/schemas/booking.py`：`BookingApplicationForm`（routes.md 2.5：`extra='forbid'`、時間分鐘 ∈ {0, 30} 且秒 / 微秒為 0、`start_time < end_time`、各欄位長度與範圍，AC9、AC15），以及 `BookingApplicationCreated`、`BookingApplicationView`；Pydantic 錯誤以 `to_field_errors`（T-003）轉逐欄訊息。
- [ ] `app/services/booking_service.py` `BookingService.apply(actor, payload, today)`，依 overview.md 第 6 節順序檢查，例外類型與訊息依 routes.md 2.5「`POST /bookings` 錯誤對照」表：
  1. 角色須為 `student`，否則 `PermissionDeniedError`（AC4）。
  2. 須為所選社團負責人（`club_repository.is_manager`），否則 `PermissionDeniedError(reason='not_club_manager', resource='club', resource_id=club_id)`（AC3；`access.denied` 由全域 handler 記錄，service 不寫日誌）。
  3. 社團須啟用中，否則 **`FieldErrors({'club_id': '此社團目前無法申請'})`**（`club_inactive`）。
  4. 場地存在且啟用（`FieldErrors` 於 `venue_id`，AC14）；人數不超過容納人數（`FieldErrors` 於 `expected_attendees`，AC15）。
  5. 時段在 `OPEN_TIME`–`CLOSE_TIME` 內（`BusinessRuleError('outside_opening_hours')`，AC8）。
  6. 非不開放日（`closures_on`，`BusinessRuleError('closed_date')`，訊息含原因類型，AC10）。
  7. 在學期區間內（呼叫 T-014 的 `is_in_semester`，`BusinessRuleError('outside_semester')`，AC17）。
  8. R-13：`can_apply(today, date)`（T-014），否則 `BusinessRuleError('apply_deadline_passed')`，訊息含最晚申請日（AC11～AC13）。
  9. 以 `local_to_utc`（T-003 timeutils）組合 UTC 區間，呼叫 T-018 `create_if_no_overlap`；衝突 → `BookingConflictError`（AC5～AC7）；鎖逾時 → `ServiceBusyError`（service 只拋例外、不處理 HTTP；**T-001 最終複審 NB-5**：轉成回應時由 T-020 route 或 T-023 handler 以 T-023 的 `RETRY_AFTER_SECONDS` 帶 `Retry-After`，service 不得自訂重試秒數）。
- [ ] 交易：規則檢查使用請求 Session 的唯讀交易，寫入由 `create_if_no_overlap` 的 `immediate_transaction` 結束唯讀交易後開新交易（ADR-003 2.1）。
- [ ] `BookingService.get_own_application(actor, booking_id)`：不存在 → `NotFoundError`；存在但非本人 → `PermissionDeniedError(reason='not_owner', resource='booking_application', resource_id=booking_id, conceal=True)`（error-handling.md 第 2 節資源隱藏規則；供 T-020）。
- [ ] 安全日誌：`booking.created`，欄位依 security-logging.md 第 2 節（不記錄活動名稱、活動說明）。
- [ ] `routers/deps.py` 新增 `get_booking_service` 工廠。
- [ ] 單元測試：上述每一條規則的通過與拒絕路徑（斷言例外類型與 `BusinessRuleError.code`）、檢查順序（例如不開放日且學期外 → `closed_date`）、AC1 成功情境、AC11～AC13 日期範例（`today` 以參數注入）、**AC17 服務層錯誤訊息測試（四個邊界日期與前後一天）**、`club_inactive`、`get_own_application` 三種結果、`booking.created` 日誌欄位不含活動內容。

## 技術備註
- 學期函式 `is_in_semester` 與 `TERM_RULES` 由 **T-014** 提供並測試；本 Task 只負責使用與 AC17 服務層測試。
- 新增相依 T-009：社團負責人檢查使用 `club_repository.is_manager`（overview.md 3.2）。
- 不開放期間資料只用於第 6 步，**不**用於 R-13 計算（US-004 AC13）。
- 每次借用（含未來固定借用時段）都需社團送出申請（使用者決定）。
- 停權檢查（US-019）未來插在「社團啟用中」之後；寒暑假時段（US-018）未來取代學期區間步驟（overview.md 第 6 節、ADR-006 第 2 節），本 Task 不實作。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（A01 存取控制、IDOR、輸入驗證）
- [ ] QA 驗收通過
- [ ] 文件與 .env.example 已更新
