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
依 AGENTS.md 1.3 與 ADR-003，實作借用申請的「檢查衝突 + 寫入」原子操作，確保同一場地不會有重疊的佔用申請，並以併發測試驗證（US-004 AC5、AC6、AC7）。

## 完成條件
- [ ] `app/repositories/booking_repository.py`：
  - `find_overlapping(venue_id, start_at, end_at)`：以半開區間判斷 `existing.start_at < new.end_at AND existing.end_at > new.start_at`，只考慮佔用狀態（`pending`、`approved`）。
  - `create_if_no_overlap(...)`：在 `immediate_transaction`（T-004）中先查詢衝突、無衝突才 insert；有衝突拋出 `BookingConflictError`。
- [ ] 只使用 ORM 或 bind parameter，不以字串拼接 SQL。
- [ ] 單元 / 整合測試：
  - AC5：19:00–21:00、17:00–18:30、18:00–20:00 皆衝突；`rejected`、`cancelled` 不算衝突。
  - AC6：相鄰 20:00–22:00 成功。
  - AC7：以多執行緒（各自獨立連線，同一個暫存 SQLite 檔案）同時寫入同一時段，只有一筆成功、其餘收到衝突；最後資料庫中無重疊佔用申請。測試需穩定（重複執行不 flaky）。

## 技術備註
- 商業規則（開放時間、不開放日、R-13、權限）不在本 Task，由 T-019 在呼叫本 repository 前檢查。
- 申請狀態只有 `pending`（審核中）、`approved`（已核准）、`rejected`（已駁回）、`cancelled`（已取消），不含「退回補件」；佔用狀態集合定義為單一來源常數，供 T-013、T-016 共用。
- **未來擴充（不在 Sprint 1 實作）**：固定保留時段（US-009，fixed reservation）建立後，需納入佔用判斷——`find_overlapping` 也要比對同場地當日的固定保留時段；設計上請讓衝突查詢集中在本 repository，日後擴充不需修改 T-019。
- 若 `busy_timeout` 逾時，需轉為明確的錯誤（例如「系統忙碌，請稍後再試」）而非 500。

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
