---
id: T-018
title: 時段重疊檢查與 BEGIN IMMEDIATE 寫入
story: US-004
status: todo        # todo / in-progress / review / done / blocked
assignee: backend-developer
branch: feature/T-018-booking-overlap-transaction
sprint: sprint-01
depends_on: [T-004, T-005]
created: 2026-11-06
---

# T-018 時段重疊檢查與 BEGIN IMMEDIATE 寫入

## 說明
依 AGENTS.md 1.3 與 ADR-003 第 1、3 節，實作借用申請的「檢查衝突 + 寫入」原子操作，確保同一場地不會有重疊的佔用申請，並以確定性鎖測試與併發測試驗證（US-004 AC5、AC6、AC7）。
本 repository 的佔用查詢也供 T-013（受影響申請）與 T-016（週檢視）使用。

## 完成條件
- [ ] `app/repositories/booking_repository.py`，介面依 ADR-003 第 3 節：
  - `NewBookingApplication`（frozen dataclass，`start_at` / `end_at` 為 aware UTC）。
  - `find_overlapping(venue_id, start_at, end_at)`：半開區間 `existing.start_at < new.end_at AND existing.end_at > new.start_at`，只考慮 `OCCUPYING_STATUSES`。
  - `create_if_no_overlap(new)`：在 `immediate_transaction`（T-004）中檢查衝突並建立 `pending` 申請；有衝突拋 `BookingConflictError`；寫鎖逾時以 `translate_busy_error` 轉 `ServiceBusyError`（不得變成 500）。
  - `list_occupying_between(start_at, end_at, venue_id=None)`（T-013、T-016 共用）與 `get_by_id(booking_id)`。
- [ ] 只使用 ORM bind parameter，不以字串拼接 SQL；不使用 `func.now()` / `CURRENT_TIMESTAMP` 參與比較。
- [ ] 測試（ADR-003 第 6 節「重疊規則」「確定性鎖測試」「併發」「不變量」四列）：
  - AC5：既有 18:00–20:00，新 19:00–21:00、17:00–18:30、18:00–20:00 → 衝突；既有為 `rejected` / `cancelled` → 成功；不同場地同時段 → 成功。
  - AC6：相鄰 20:00–22:00 成功。
  - 確定性鎖：連線 A 持有 `immediate_transaction`，連線 B（timeout 0.1 秒）→ `ServiceBusyError`；A 寫入同時段並 commit 後 B 重試 → `BookingConflictError`。
  - AC7 併發：同一 `tmp_path` SQLite 檔、`threading.Barrier(8)`、8 個執行緒各自 `session_factory()` 同時寫入同一時段，恰 1 成功、7 個 `BookingConflictError`、0 個 `ServiceBusyError`；`parametrize` 重複 20 輪。
  - 不變量：測試結束以自我 JOIN 斷言同場地不存在任何一對重疊的佔用申請。

## 技術備註
- 商業規則（開放時間、不開放日、學期、R-13、權限）不在本 Task，由 T-019 在呼叫前檢查，不放進寫鎖交易。
- 佔用狀態集合 `OCCUPYING_STATUSES` 由 T-005 定義於 `app/models/enums.py`，本 Task 只使用。
- **未來擴充（不在 Sprint 1 實作）**：固定保留時段（US-009）的衝突規則見 ADR-003 第 5 節；衝突查詢集中在本 repository，日後擴充不需修改 T-019。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（Injection、資料一致性）
- [ ] QA 驗收通過
- [ ] 文件與 .env.example 已更新
