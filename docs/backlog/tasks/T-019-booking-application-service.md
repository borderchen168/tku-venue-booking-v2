---
id: T-019
title: 借用申請 service（規則驗證、授權、日誌）
story: US-004
status: todo        # todo / in-progress / review / done / blocked
assignee: backend-developer
branch: feature/T-019-booking-application-service
sprint: sprint-01
depends_on: [T-008, T-011, T-013, T-014, T-018]
created: 2026-11-06
---

# T-019 借用申請 service（規則驗證、授權、日誌）

## 說明
整合場地、不開放期間（R-03～R-05，來自 T-013）、工作天計算（R-13，T-014 純函式，只算週一～週五）與重疊檢查，實作學生以社團名義申請臨時借用的商業邏輯（US-004）。

## 完成條件
- [ ] `app/schemas/booking.py`：社團 id、場地 id（正整數）、日期、開始 / 結束時間、活動名稱 1～100 字、活動說明 1～1000 字、預估人數 1～9999（AC15）；時間須為 30 分鐘整數倍、開始早於結束、同一天（AC9）。
- [ ] `app/services/booking_service.py` `apply(user, payload, today)`，依序檢查並回傳可區分的錯誤：
  1. 角色須為 `student`，`staff` → 權限錯誤（AC4）。
  2. 使用者須為所選社團負責人，否則權限錯誤並記錄權限拒絕日誌（AC3，IDOR 防護）。
  3. 場地啟用且存在（AC14）；預估人數不超過容納人數（有設定時，AC15）。
  4. 時段在 08:00–22:00 內（R-01，AC8）。
  5. 日期非不開放日，錯誤訊息含原因類型（AC10）。
  6. 符合 R-13：`today`（Asia/Taipei）≤ 最晚申請日（T-014，只算週一～週五，不傳入不開放期間或國定假日資料），錯誤訊息含最晚申請日（AC 編號以 PO 修訂後的 US-004 為準）。
  7. 呼叫 T-018 `create_if_no_overlap` 建立 `pending` 申請；衝突 → 「該時段已被借用」（AC5～AC7）。
- [ ] 以 Asia/Taipei 組合日期時間後轉 UTC 儲存。
- [ ] 安全日誌：申請建立（申請 id、user id、club id），不記錄活動說明等完整內容。
- [ ] 單元測試涵蓋上述每一條規則的通過與拒絕路徑，以及 AC1 成功情境（使用 AC 中的日期範例，`today` 由參數注入）。

## 技術備註
- 仍依賴 T-013：用於第 5 步檢查日期是否落在不開放日期（R-03～R-05）；但不開放期間資料**不**用於 R-13 計算。
- 每次借用（含未來固定借用時段）都需社團送出申請（使用者決定）。
- 停權檢查於 US-019 加入，本 Task 預留檢查點即可（不實作）。
- 寒暑假時段（R-02，US-018）不在本 Sprint。

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
