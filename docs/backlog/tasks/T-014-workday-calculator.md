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
以純函式實作 R-13「活動前 5 個工作天」的最晚申請日計算（ADR-004 第 4 節），以及學期區間判斷 `is_in_semester`（ADR-006 第 1 節）。
依使用者決定（2026-11-06），本階段**工作天＝週一～週五**，不考慮國定假日與補班；學期區間為每年 9/1～12/31、3/1～6/30。
兩個模組都不依賴資料庫、設定或 `Clock`，可與基礎建設平行開發；T-016、T-019 使用本 Task 的函式。

## 完成條件
- [ ] `app/services/workday.py`：`REQUIRED_WORKDAYS`、`is_workday`、`latest_apply_date`、`can_apply`，簽章與行為依 ADR-004 第 4 節（`workdays < 1` 拋 `ValueError`；不接受假日 / 不開放期間參數）。
- [ ] `app/services/semester.py`：`Term`、`TermRule`、`TERM_RULES`、`is_in_semester(day, rules=TERM_RULES)`，依 ADR-006 第 1 節。**`Semester` 與 `semester_of` 不在 Sprint 1 實作**（屬 US-009 / US-020）。
- [ ] 兩個模組只匯入標準函式庫（overview.md 第 2 節匯入規則），一律 `import datetime as dt`。
- [ ] 單元測試（`pytest.mark.parametrize`）：
  - 工作天：ADR-004 第 4 節驗證範例（2026-11-16 → 2026-11-09、2026-11-21 → 2026-11-16、2026-11-23 → 2026-11-16、2027-01-04 → 2026-12-28）；2026-11-10 對 2026-11-16 `can_apply` 為 False；活動日為週日；跨月、跨年；`is_workday` 對週一～週日七天；`workdays=0` 拋錯。
  - 學期：ADR-006 第 1 節列出的 True / False 日期（含 AC17 四個邊界與前後一天、2028-02-29 閏年）；`TERM_RULES` 每條規則起月日 ≤ 迄月日且規則間不重疊。

## 技術備註
- 「今天」以 `APP_TIMEZONE` 日期判斷，由呼叫端（T-016、T-019）以 `Clock.today_local()` 傳入，本模組不呼叫 `datetime.now()` / `date.today()`。
- 只相依 T-003（套件骨架與工具設定）；**不相依** T-013。
- T-019 只負責使用 `is_in_semester` 並撰寫 AC17 的服務層錯誤訊息測試；學期函式本身的正確性由本 Task 測試保證。
- 國定假日、補班日本階段不處理（使用者決定）。

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
