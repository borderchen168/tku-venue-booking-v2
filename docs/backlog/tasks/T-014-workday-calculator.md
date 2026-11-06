---
id: T-014
title: R-13 工作天與最晚申請日計算
story: US-004
status: todo        # todo / in-progress / review / done / blocked
assignee: backend-developer
branch: feature/T-014-workday-calculator
sprint: sprint-01
depends_on: [T-003]
created: 2026-11-06
---

# T-014 R-13 工作天與最晚申請日計算

## 說明
以純函式實作 R-13「活動前 5 個工作天」的最晚申請日計算。依使用者決定（2026-11-06），本階段**工作天＝週一～週五**，
不考慮國定假日與補班，也不依賴不開放期間（T-013）或任何資料庫資料，可與基礎建設平行開發。

## 完成條件
- [ ] `app/services/workday.py`（或依 T-001 指定位置）：
  - `is_workday(day: date) -> bool`：週一至週五為 True，週六、週日為 False。
  - `latest_apply_date(event_date: date, workdays: int = REQUIRED_WORKDAYS) -> date`：由活動日往前推算第 5 個工作天（活動日本身不計）。
  - `can_apply(today: date, event_date: date) -> bool`：`today <= latest_apply_date(event_date)`。
- [ ] 工作天數 5 定義為單一來源常數 `REQUIRED_WORKDAYS`。
- [ ] 函式簽章不接受假日 / 不開放期間參數；日後若需支援國定假日，以新 Task 擴充。
- [ ] 單元測試（以 `pytest.mark.parametrize`）：
  - US-004 範例：活動日 2026-11-16（一）→ 最晚申請日 2026-11-09（一），2026-11-10 申請被拒。
  - US-004 範例：活動日 2026-11-21（六）→ 最晚申請日 2026-11-16（一），當天可申請。
  - 區間內含國定假日的平日（例如 2027-01-01（五））仍算工作天，不影響結果。
  - 活動日為週日；跨月、跨年邊界；`is_workday` 對週一～週日七天的結果。
  - AC 編號以 PO 修訂後的 US-004 為準。

## 技術備註
- 「今天」以 Asia/Taipei 日期判斷，由呼叫端（T-019）傳入，本模組不呼叫 `datetime.now()`，以利測試。
- 只相依 T-003（套件骨架與工具設定）；**不相依** T-013。
- 國定假日、補班日本階段不處理（使用者決定）。不開放日期（R-03～R-05）是否可借由 T-019 另外檢查，與 R-13 無關。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（不適用）
- [ ] QA 驗收通過
- [ ] 文件與 .env.example 已更新
