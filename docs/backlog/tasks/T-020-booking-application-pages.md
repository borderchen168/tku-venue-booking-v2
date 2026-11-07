---
id: T-020
title: 借用申請表單與送出結果頁
story: US-004
status: todo        # todo / in-progress / review / done / blocked
assignee: frontend-developer
branch: feature/T-020-booking-application-pages
sprint: sprint-01
depends_on: [T-010, T-017, T-019]
created: 2026-11-06
---

# T-020 借用申請表單與送出結果頁

## 說明
依 routes.md 2.5 實作學生申請臨時借用的表單頁、送出處理與結果頁（`/bookings/new`、`POST /bookings`、`/bookings/{booking_id}`），完成 US-004 的使用者可見流程。

## 完成條件
- [ ] `GET /bookings/new`：`require_role('student')`；未登入 → `303 /login?next=…`（AC2）；staff → 403（AC4）；社團下拉只列 `list_managed_by` 的啟用中社團、場地下拉只列啟用中場地、時間下拉 08:00～22:00 每 30 分鐘；`venue_id`、`date` 查詢參數可預填（無效值忽略）；沒有負責任何社團時顯示提示且不顯示表單（routes.md 2.5）。
- [ ] `POST /bookings`：CSRF 由全域 `csrf_protect` 驗證（AC16）→ `require_role('student')` → 表單字串組 `BookingApplicationForm` → `BookingService.apply(actor, payload, today)`（`today` 由 `Depends(get_clock)` 取得）→ 成功 `303 /bookings/{id}`。
- [ ] 失敗處理依 routes.md 2.5「`POST /bookings` 錯誤對照」表逐列實作：`FieldErrors` / `BusinessRuleError` → 422、`BookingConflictError` → 409、`ServiceBusyError`（寫鎖逾時）→ 503，皆重新渲染表單並保留已填資料；**503 重新渲染時帶 `Retry-After`，值使用 T-023 的 `RETRY_AFTER_SECONDS`，不得寫死（T-001 最終複審 NB-5）**；權限錯誤 → 403 錯誤頁（AC3、AC4）。
- [ ] `GET /bookings/{booking_id}`（`bookings/submitted.html`）：顯示申請編號、場地、日期、時段、社團、活動名稱、狀態「審核中」、「已送出，待課外組承辦人審核（R-12）」與「未核准前不得使用場地（R-16）」（AC1）；**只有申請人本人可看：不存在 → 404；存在但非本人 → 404 並記錄 `access.denied`（`reason=not_owner`，`get_own_application` 拋 `conceal=True` 的例外，由全域 handler 記錄）**；staff → 403。
- [ ] **router 註冊**（ADR-002 2.1、overview.md 3.1）：router 宣告為 `APIRouter(prefix=..., route_class=LimitedFormRoute)`（prefix 只宣告在 router 上、不得再 `include_router` 其他 router，T-001 最終複審 NB-1 / NB-2），並**加入 `app/routers/__init__.py` 的 `ALL_ROUTERS`**（`create_app` 只從此清單掛載，未加入即不會被掛載）。
- [ ] **POST 路徑登錄**：把 `/bookings` 加入 `tests/integration/test_route_coverage.py` 的 `EXPECTED_POST_PATHS`（T-023 建立；路徑以 routes.md 為準），並確認該測試的「每個 `APIRoute` 都是 `LimitedFormRoute`」「POST 不帶 Token → 403」通過。
- [ ] 整合測試：AC1（送出後借用狀況頁顯示審核中）、AC2（GET 導向登入；POST 情境同 T-022）、AC3（竄改 `club_id` → 403 + `access.denied`）、AC4、AC16、至少一個 422 規則錯誤（含資料保留）、409 重疊、非本人存取 `/bookings/{id}` 回 404 且 `caplog` 有 `access.denied`、不存在 id 回 404 且無 `access.denied`、兩者回應本體相同；寫鎖逾時（monkeypatch 拋 `ServiceBusyError`）→ 503 重新渲染且 `Retry-After` 等於 `RETRY_AFTER_SECONDS`。

## 技術備註
- 可寫入：`app/templates/`、`app/static/`、`app/routers/web/`、`tests/`。
- route 以 `Form()` 收字串，自行建立 Pydantic schema 並捕捉 `ValidationError`（overview.md 第 5 節）；router 不直接操作 DB Session、不匯入 `repositories`。
- `ALL_ROUTERS` / `EXPECTED_POST_PATHS`、`RETRY_AFTER_SECONDS` 由 T-023 建立；本 Task 經 T-010 → T-008 → T-007 → T-023 間接相依，不另列 depends_on。
- 「申請此場地」入口已由 T-017 依 `DayAvailability.status == bookable`（`bookable` property）顯示，本 Task 只需處理預填；預填不代表規則通過，送出時仍由 T-019 完整檢查。
- router 一律 `APIRouter(route_class=LimitedFormRoute)`（T-023，ADR-002 2.1）；表單為 urlencoded，不得使用 `enctype="multipart/form-data"`（routes.md 第 1 節）。
- （2026-11-07 routes.md 第 4 版同步） **Code Review 檢查項**：route 傳給 `TemplateResponse` 的 context 不得含保留名稱 `request`、`current_user`、`csrf_token`、`messages`、`app_timezone`（會被 context processor 覆蓋，routes.md 3.1）；需要改變其值時改設 `request.state`。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（CSRF、存取控制）
- [ ] QA 驗收通過（US-004）
- [ ] 文件與 .env.example 已更新
