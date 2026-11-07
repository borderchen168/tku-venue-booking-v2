---
id: T-015
title: 不開放期間管理頁
story: US-017
status: todo        # todo / in-progress / review / done / blocked
assignee: frontend-developer
branch: feature/T-015-closed-period-admin-pages
sprint: sprint-01
depends_on: [T-002, T-010, T-013]
created: 2026-11-06
---

# T-015 不開放期間管理頁

## 說明
依 routes.md 2.4 實作承辦人專用的不開放日期 / 期間管理頁（`/admin/closed-periods*`：列表、新增、檢視、編輯、刪除），完成 US-017。

## 完成條件
- [ ] 列表頁 `admin/closed_periods/list.html`：依 `start_date` 遞減列出起日、迄日、原因類型、說明與操作（檢視、編輯、刪除）（AC1、AC4）。
- [ ] 新增 / 編輯表單 `form.html`：起日、迄日（`type="date"`）、類型（下拉白名單）、說明（欄位名依 routes.md 第 4 節）；驗證失敗 `422` 逐欄顯示錯誤並保留已填資料（AC5）。
- [ ] 新增成功：flash「已新增不開放期間，受影響的既有申請 N 筆」→ `303 /admin/closed-periods/{id}`；**檢視頁 `detail.html` 列出 `ClosedPeriodDetail.affected` 受影響的既有申請**（欄位依 routes.md 2.4；取消連結待 US-012）（AC3）。
- [ ] 刪除：`GET .../delete` 顯示確認頁 `confirm_delete.html`（不用 JS confirm，配合 CSP），`POST .../delete` 執行刪除 → `303 /admin/closed-periods`；GET 不改變狀態。
- [ ] 所有路由套用 `require_role('staff')`：學生 403（`access.denied` 由全域 handler 記錄）、未登入 `303 /login?next=...`（AC6）；所有 POST 由全域 `csrf_protect` 驗證（AC7）；不存在的 `period_id` → 404。
- [ ] **router 註冊**（ADR-002 2.1、overview.md 3.1）：router 宣告為 `APIRouter(prefix=..., route_class=LimitedFormRoute)`（prefix 只宣告在 router 上、不得再 `include_router` 其他 router，T-001 最終複審 NB-1 / NB-2），並**加入 `app/routers/__init__.py` 的 `ALL_ROUTERS`**（`create_app` 只從此清單掛載，未加入即不會被掛載）。
- [ ] **POST 路徑登錄**：把 `/admin/closed-periods`、`/admin/closed-periods/{period_id}/edit`、`/admin/closed-periods/{period_id}/delete`（縮減順序第 2 項啟用時不含 `edit`，同步告知 T-022） 加入 `tests/integration/test_route_coverage.py` 的 `EXPECTED_POST_PATHS`（T-023 建立；路徑以 routes.md 為準），並確認該測試的「每個 `APIRoute` 都是 `LimitedFormRoute`」「POST 不帶 Token → 403」通過。
- [ ] 整合測試：AC1、AC3、AC4、AC5、AC6、AC7（含學生 403 且 `caplog` 有 `access.denied`、未登入導向、缺少 CSRF 403 且資料不變、新增後檢視頁列出受影響申請）。

## 技術備註
- 可寫入：`app/templates/`、`app/static/`、`app/routers/web/`、`tests/`。
- route 檔 `app/routers/web/admin_closed_periods.py`（overview.md 3.2）。
- `ALL_ROUTERS` / `EXPECTED_POST_PATHS` 由 T-023 建立；本 Task 經 T-010 → T-008 → T-007 → T-023 間接相依，不另列 depends_on。
- router 一律 `APIRouter(route_class=LimitedFormRoute)`（T-023，ADR-002 2.1）；表單為 urlencoded，不得使用 `enctype="multipart/form-data"`（routes.md 第 1 節）。
- 縮減順序啟動時（planning.md）：AC3 檢視頁受影響清單區塊可移除；AC4「編輯」兩條 route 可延後（routes.md 2.4 註）。
- （2026-11-07 routes.md 第 4 版同步） **Code Review 檢查項**：route 傳給 `TemplateResponse` 的 context 不得含保留名稱 `request`、`current_user`、`csrf_token`、`messages`、`app_timezone`（會被 context processor 覆蓋，routes.md 3.1）；需要改變其值時改設 `request.state`。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（存取控制、CSRF）
- [ ] QA 驗收通過（US-017）
- [ ] 文件與 .env.example 已更新
