---
id: T-016
title: 借用狀況週檢視查詢 service
story: US-002
status: todo        # todo / in-progress / review / done / blocked
assignee: backend-developer
branch: feature/T-016-availability-service
sprint: sprint-01
depends_on: [T-011, T-013, T-014, T-018]
created: 2026-11-06
---

# T-016 借用狀況週檢視查詢 service

## 說明
依 routes.md 2.3「週檢視 service」提供「單一場地 × 一週」的借用狀況資料：佔用中的申請（只含公開欄位）、不開放日期、學期區間標記，以及每日單一的 **`DayStatus`**（`closed` / `outside_semester` / `deadline_passed` / `bookable`，對應 US-002 AC4、AC6～AC8），
時間轉換為 `APP_TIMEZONE`，供 T-017 頁面使用。

## 完成條件
- [ ] `app/schemas/availability.py`：`DayStatus`（`StrEnum`：`CLOSED`、`OUTSIDE_SEMESTER`、`DEADLINE_PASSED`、`BOOKABLE`）、`PublicBookingSlot`、`DayAvailability`（`date`、**`status: DayStatus`**、`closed_reason_types`、`in_semester`、`bookings`；**`bookable` 為 `@property`**，回傳 `status is DayStatus.BOOKABLE`，不是欄位）、`WeekAvailability`，欄位依 routes.md 2.3；每筆借用**只含**公開欄位（US-002 AC2）。
- [ ] `app/services/availability_service.py` `AvailabilityService.get_week(venue_id, week_start_raw, today) -> WeekAvailability`：
  - `week_start_raw` 為 None → 本週；任意日期正規化為該週週一。
  - 格式不是 `YYYY-MM-DD`，或正規化後的週一不在 **`[monday(today − 365 天), monday(today + 365 天)]`（含兩端）** → 拋 **`FieldErrors({'week_start': '日期格式錯誤或超出可查詢範圍（前後一年）'})`**（US-002 AC5）；`prev_week_start` / `next_week_start` 超出範圍時為 `None`。
  - 場地停用或不存在 → `NotFoundError`（沿用 T-011）。
  - 佔用申請透過 T-018 `BookingRepository.list_occupying_between`（以 `local_day_bounds_utc` 換算週區間），只回傳 `pending` / `approved`（AC3）；查詢層只 select 公開欄位，不載入申請人、活動說明。UTC → `APP_TIMEZONE` 後依當地日期分組（ADR-004）。
  - 不開放日：`ClosedPeriodService.closures_between`（T-013）；不開放日仍列出既有佔用。
  - `in_semester = is_in_semester(day)`（T-014）。
  - **`status` 依 routes.md 2.3 優先規則，由上而下第一個成立者為結果**：① `closed_reason_types` 非空 → `closed`（即使同時在學期外，AC6）；② `not in_semester` → `outside_semester`；③ `not can_apply(today, day)`（T-014，**含過去日期**）→ `deadline_passed`；④ 其他 → `bookable`（US-002 AC4、AC6～AC8）。順序與 `BookingService.apply` 的檢查順序一致（不開放 → 學期 → R-13，overview.md 第 6 節）。
  - `closed_reason_types` 去重、依列舉順序；`status=closed` 時必非空。任何 `status` 下 `bookings` 都列出既有佔用。
  - 純讀取，使用預設 deferred 交易（ADR-003 2.1）。
- [ ] 單元測試：AC1 範例資料（10:00–12:00 已核准、14:00–16:00 審核中）、AC3、AC4（期中考週、國定假日 → `closed` 且原因類型正確）、AC5（不合法格式、範圍兩端恰好在內 / 外一週、正規化週一）、AC6（2026-12-28 那一週：12-28～12-31 依一般規則、2027-01-01 起 `outside_semester`；**學期外且同時為不開放日 → `closed`**）、AC7 / AC8（today=2026-11-16：學期內一般日 → `bookable`、不開放日 → `closed`、學期外 → `outside_semester`、2026-11-20 已過 R-13 期限 → `deadline_passed`、今天以前的過去日期 → `deadline_passed`）、`bookable` property 只在 `status=bookable` 時為 True、`prev/next_week_start` 邊界為 `None`、輸出 schema 不含個資欄位。

## 技術備註
- 申請狀態只有四種，不含「退回補件」（使用者決定）。
- `status` / `bookable` 只用於顯示（空閒時段標示與「申請此場地」連結），不含個資；申請時 T-019 仍完整檢查所有規則（routes.md 2.3）。
- US-002 AC6～AC8 已由 PO 寫入（overview.md 第 11 節 #4）；本 Task 只提供 `status`，標示文字由 T-017 處理。
- `DayStatus` 的負責 Task 為本 Task（overview.md 3.1），T-017 只使用、不改簽章。
- 新增相依 T-014（`is_in_semester`、`can_apply`）與 T-018（`list_occupying_between`）。
- 固定保留時段（US-009）未來需一併顯示於週檢視，不在 Sprint 1 實作。
- 測試資料中的借用申請直接以 repository / model 建立，不依賴 T-019；「今天」以參數注入。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（資料最小化、個資不外洩）
- [ ] QA 驗收通過
- [ ] 文件與 .env.example 已更新
