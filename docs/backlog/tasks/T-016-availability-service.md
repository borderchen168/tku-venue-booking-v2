---
id: T-016
title: 借用狀況週檢視查詢 service
story: US-002
status: todo        # todo / in-progress / review / done / blocked
assignee: backend-developer
branch: feature/T-016-availability-service
sprint: sprint-01
depends_on: [T-011, T-013]
created: 2026-11-06
---

# T-016 借用狀況週檢視查詢 service

## 說明
提供「單一場地 × 一週」的借用狀況資料：佔用中的申請（只含公開欄位）與不開放日期，時間轉換為 Asia/Taipei，供 T-017 頁面使用。

## 完成條件
- [ ] `app/schemas/availability.py`：公開輸出 schema，每筆借用**只含**場地、日期、起訖時間、活動名稱、主辦社團名稱、狀態（AC2）；每日含不開放標記與原因類型（AC4）。
- [ ] `app/services/availability_service.py`：
  - 查詢層只 select 公開欄位（不載入申請人、活動說明等欄位），避免個資外洩。
  - 佔用狀態：`pending`（顯示「審核中」）、`approved`（顯示「已核准」）；`rejected`、`cancelled` 不回傳（AC3）。申請狀態只有這四種，不含「退回補件」（使用者決定：不補件，直接退回重新申請）。
  - 週起始日正規化為週一；查詢範圍限今天（Asia/Taipei）前後各 1 年，超出或不合法時拋出驗證例外（AC5）。
  - UTC → Asia/Taipei 轉換使用 `zoneinfo`（`APP_TIMEZONE` 設定）。
  - 場地停用或不存在時沿用 T-011 的 NotFound。
- [ ] 單元測試：AC1 範例資料（10:00–12:00 已核准、14:00–16:00 審核中）、AC3、AC4（期中考週、國定假日）、AC5 範圍邊界、輸出 schema 不含個資欄位。

## 技術備註
- 原 US-002「退回補件對外顯示為審核中」的規則已因使用者決定移除；AC 編號以 PO 修訂後的 Story 為準。
- 固定保留時段（US-009）未來需一併顯示於週檢視，不在 Sprint 1 實作。
- 若需要測試資料中的借用申請，於測試中直接以 repository / model 建立，不依賴 T-019。

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
