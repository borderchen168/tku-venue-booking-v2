---
id: T-017
title: 借用狀況週檢視頁
story: US-002
status: todo        # todo / in-progress / review / done / blocked
assignee: frontend-developer
branch: feature/T-017-availability-page
sprint: sprint-01
depends_on: [T-002, T-012, T-016]
created: 2026-11-06
---

# T-017 借用狀況週檢視頁

## 說明
依 routes.md 2.3 實作公開（不需登入）的單一場地週借用狀況頁 `GET /venues/{venue_id}/availability`，完成 US-002，並在學生登入時提供申請入口（US-004 AC1）。

## 完成條件
- [ ] `venues/availability.html` 週檢視表格：列 08:00–22:00（`open_time` / `close_time` / `slot_minutes`，30 分鐘一格）、欄為週一至週日。每日依 `DayAvailability.status`（T-016）標示，對照 routes.md 2.3 優先規則表：
  - `closed` → 整天「不開放（原因類型）」（以 `reason_type_label` filter 顯示，US-002 AC4；學期外且同時為不開放日亦同，AC6）。
  - `outside_semester` → 整天「不開放（非學期期間）」（AC6）。
  - `deadline_passed` → 空閒時段「已過申請期限」（**含過去日期**，AC8）。
  - `bookable` → 空閒時段「可申請」（AC1、AC8）。
  - 既有佔用（`bookings`）在任何 `status` 下都依狀態標示「已核准」/「審核中」（`status_label` filter），覆蓋該時段的空閒標示（AC1、AC8）。
  - 樣板只依 `status` 分支，**不自行重算**學期、不開放或 R-13；配色依 T-002 style-guide，且不只以顏色區分（附文字，無障礙）。
- [ ] 學生登入時，**只在 `status=bookable`（`day.bookable`）的日期**顯示「申請此場地」連結 → `/bookings/new?venue_id=..&date=..`（routes.md 2.3、US-002 AC7）；訪客與承辦人一律不顯示。所有訪客看到相同的狀態標示（AC8），只有連結依角色顯示。
- [ ] 上一週 / 下一週導覽（`prev_week_start` / `next_week_start` 為 `None` 時不顯示）與 `week_start` 查詢參數（宣告為 `str | None`，由 service 驗證；GET 表單，不需 CSRF）。
- [ ] `week_start` 無效（service 拋 `FieldErrors`）：route 改呼叫 `get_week(venue_id, None, today)`，以 **`422`** 渲染本週並在頂部顯示「日期格式錯誤或超出可查詢範圍（前後一年）」（US-002 AC5）；場地停用 / 不存在 → 404；`venue_id` 非正整數 → 422 錯誤頁。
- [ ] `today` 由 `Depends(get_clock)` 取得後傳入 service（overview.md 2.1）。
- [ ] 活動名稱、社團名稱經 autoescape 輸出（CWE-79）。
- [ ] 場地資訊頁（T-012）的連結可正確進入本頁。
- [ ] **router 註冊**（ADR-002 2.1、overview.md 3.1）：router 宣告為 `APIRouter(prefix=..., route_class=LimitedFormRoute)`（prefix 只宣告在 router 上、不得再 `include_router` 其他 router，T-001 最終複審 NB-1 / NB-2），並**加入 `app/routers/__init__.py` 的 `ALL_ROUTERS`**（`create_app` 只從此清單掛載，未加入即不會被掛載）。
- [ ] 確認 T-023 的 `tests/integration/test_route_coverage.py` 通過（本頁只有 GET；若與 T-012 共用 venues router 則不需另行加入清單，只需確認 route 掛在已登錄的 router 上，不需擴充 `EXPECTED_POST_PATHS`）。
- [ ] 整合測試（以 `dependency_overrides[get_clock]` 固定 today=2026-11-16）：
  - US-002 AC1～AC5：AC1 範例資料標示、頁面原始碼不含申請人姓名、帳號、活動說明（AC2）、已取消 / 已駁回不顯示（AC3）、不開放日與原因類型（AC4）、XSS 字串被跳脫、無效 `week_start` 回 422 且顯示本週（AC5）。
  - AC6：2026-12-28 那一週，2027-01-01～01-03 顯示「不開放（非學期期間）」；與不開放日重疊時顯示原因類型。
  - AC7：學生登入時連結只出現在 `bookable` 日期；訪客與承辦人看不到連結。
  - **AC8**：同一週內可申請日顯示「可申請」、2026-11-20 與今天以前的日期顯示「已過申請期限」且不顯示「可申請」；不開放日 / 學期外日不顯示「可申請」或「已過申請期限」；未登入、學生、承辦人三種身分看到相同標示。

## 技術備註
- 可寫入：`app/templates/`、`app/static/`、`app/routers/web/`、`tests/`。
- 不使用 inline script；本頁不需要 JS。
- `ALL_ROUTERS` 由 T-023 建立；本 Task 經 T-012 → T-023 間接相依，不另列 depends_on。
- router 一律 `APIRouter(route_class=LimitedFormRoute)`（T-023，ADR-002 2.1）。
- US-002 AC6～AC8 由 PO 於 2026-11-06 寫入（AC8 為新增：空閒時段依日期標示「可申請」或「已過申請期限」）；本頁標示規則以 routes.md 2.3 優先規則表為唯一來源。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（XSS、個資）
- [ ] QA 驗收通過（US-002）
- [ ] 文件與 .env.example 已更新
