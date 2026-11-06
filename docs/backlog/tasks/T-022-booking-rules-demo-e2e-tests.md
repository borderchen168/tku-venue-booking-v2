---
id: T-022
title: 申請規則、併發與 Sprint Demo 端到端測試
story: [US-004, US-002, US-017, US-001]
status: todo        # todo / in-progress / review / done / blocked
assignee: tester
branch: feature/T-022-booking-rules-demo-e2e-tests
sprint: sprint-01
depends_on: [T-009, T-015, T-020]
created: 2026-11-06
---

# T-022 申請規則、併發與 Sprint Demo 端到端測試

## 說明
以 `TestClient` 驗證 Sprint 1 Demo 完整流程與 US-004 的所有拒絕情境（含併發），並整理 Demo 操作腳本供 Sprint Review 使用。
預期回應以 routes.md 2.5「`POST /bookings` 錯誤對照」表與 ADR-002 第 5 節為準。

## 完成條件
- [ ] 端到端測試（Demo 流程）：訪客瀏覽場地清單 → 場地資訊 → 借用狀況 → 承辦人登入並新增考試週 → 學生登入並成功申請 → 借用狀況頁顯示該時段「審核中」且不含申請人個資。
- [ ] 拒絕情境（透過 HTTP，非直接呼叫 service；斷言狀態碼與訊息依 routes.md 2.5 錯誤對照表）：時段重疊（AC5，409）、不開放日（AC10，422）、學期區間外（AC17，422）、未達 5 個工作天（AC11，422）、竄改 `club_id`（AC3，403 + `access.denied`）、staff 申請（AC4，403）、缺少 CSRF（AC16，403）、超出開放時間（AC8，422）。
- [ ] **AC2 兩種情境**（ADR-002 第 5 節）：① 未登入且不帶 Token 直接 POST `/bookings` → **403**；② 先 `GET /login` 取得登入前 Token 與 nonce Cookie 後帶 Token POST `/bookings` → **303 `/login`**。兩者都不建立申請。
- [ ] 併發：兩位不同學生各自 `TestClient`（各自 Cookie）在兩個執行緒同時 POST 同一時段，恰一個 303、一個 409（AC7，ADR-003 第 6 節「HTTP 併發」）。
- [ ] **`EXPECTED_POST_PATHS` 最終驗收**（自 T-021 移入，2026-11-06 Orchestrator 決定；ADR-002 2.1 第 3 點、routes.md 第 1 節）：在 T-023 的 `tests/integration/test_route_coverage.py`（或本 Task 測試檔）斷言 `EXPECTED_POST_PATHS` **等於** `{'/login', '/logout', '/bookings', '/admin/closed-periods', '/admin/closed-periods/{period_id}/edit', '/admin/closed-periods/{period_id}/delete'}`（以 routes.md 第 1 節為準；縮減順序第 2 項啟用時不含 `edit`），且以 `iter_api_routes(app, routers=ALL_ROUTERS)` 走訪收集到的 POST 路徑集合**也等於**此集合（沒有漏登錄、也沒有未預期的 POST route）。
- [ ] 承辦人新增不開放期間後，借用狀況頁立即標示、該期間申請立即被拒（EP-005 成功指標）。
- [ ] `docs/sprints/sprint-01/demo-script.md` 所需內容：Demo 資料建立步驟（引用 cli.md 第 5 節 / T-009 回報）與操作步驟，交由 Scrum Master 寫入 sprint 文件（tester 不寫 `docs/sprints/`，以 Task 回報提供內容）。
- [ ] 發現的缺陷寫入 `docs/backlog/bugs/`。

## 技術備註
- 可寫入：`tests/`、`docs/backlog/bugs/`。
- 「今天」以 `app.dependency_overrides[get_clock]` 注入 `FixedClock`（overview.md 2.1），確保 R-13、AC17 測試不隨實際日期變動。
- 本 Task 原本就相依 T-015、T-020，承接上述最終驗收不需新增相依。
- US-004 AC2 已由 PO 依 ADR-002 第 5 節改寫為 403 / 303 兩種情境（overview.md 第 11 節 #3）。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過
- [ ] QA 驗收通過（US-001、US-002、US-004、US-017 全部 AC）
- [ ] 文件與 .env.example 已更新
