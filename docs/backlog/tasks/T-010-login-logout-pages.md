---
id: T-010
title: 登入／登出頁面與 web route
story: US-013
status: todo        # todo / in-progress / review / done / blocked
assignee: frontend-developer
branch: feature/T-010-login-logout-pages
sprint: sprint-01
depends_on: [T-002, T-008]
created: 2026-11-06
---

# T-010 登入／登出頁面與 web route

## 說明
依 routes.md 2.1、2.2 實作登入頁、登入送出、登出與首頁的角色選單，串接 T-007 Session / CSRF（登入前為無狀態 Token）與 T-008 認證服務，完成 US-013 的使用者可見流程。

## 完成條件
- [ ] `GET /login`：**只呼叫 `issue_login_csrf_token` 發行無狀態 Token，不建立任何 DB Session**；沿用既有有效 nonce（沒有才產生），**每次回應都 `Set-Cookie` 刷新 nonce Cookie 的 `Max-Age`**（ADR-002 4.2）；`reason=timeout` 顯示「登入已逾時，請重新登入」；已登入者 `303 /`（routes.md 2.2）。
- [ ] `POST /login`：CSRF 由全域 `csrf_protect` 驗證 → `AuthService.authenticate` → 成功時 `create_session_for_user`、**刪除 nonce Cookie**、`303 <next 或 />`；所有失敗一律 `400` 重新渲染、訊息「帳號或密碼錯誤」，**`username` 回填截斷至前 50 字**、`password` 不回填，回應除 CSRF Token 值外逐字相同（ADR-005 第 3 節）。`Form()` 參數宣告為不受限 `str`（`username: str = Form('')`、`password: str = Form('')`）；route 必須為 **sync（`def`）**，與其他 sync route 共用 threadpool 的行為依 ADR-005 第 6 節。
- [ ] 雜湊名額已滿（`ServiceBusyError`，**不等待、立即**）→ 503 頁（error-handling.md 第 3 節、ADR-005 第 3、6 節）；此時不消耗登入嘗試次數。
- [ ] `POST /logout`：**無有效已登入 Session（未登入、已逾時）→ 403**（`CSRFError(reason='no_session')`，錯誤頁附回首頁連結）；成功 `destroy_session` → `303 /`、記錄 `auth.logout`（routes.md 2.2）。
- [ ] 首頁 `GET /`：依 routes.md 2.1 顯示 `display_name` 與角色選單（學生：申請場地；承辦人：不開放期間管理）；**Sprint 1 未完成的「我的申請」（US-005）、「待審核」（US-006）隱藏，不出現在選單**（US-013 AC1）；未登入顯示場地清單入口與登入連結。
- [ ] `next` 參數以 `is_safe_next` 驗證（routes.md 2.6，防 Open Redirect(開放式重新導向)，CWE-601），導向只用相對路徑。
- [ ] （2026-11-07 routes.md 第 4 版同步） **登入樣板改用 `next_path`**（routes.md 2.6、3.2）：`GET /login` 與 `POST /login` 失敗重新渲染時，route 先以 `is_safe_next()` 過濾，**不合格改為 `/`**，再以 context 變數 `next_path: str` 傳給 `auth/login.html`；樣板**只能**輸出於 `<input type="hidden" name="next" value="{{ next_path }}">`（加雙引號、autoescape），**不得**直接讀 `request.query_params['next']`，且 `next`（含過濾後的值）不得出現在 `<a href>`、`<form action>`、`<meta http-equiv="refresh">` 或任何 URL 屬性中。
- [ ] **router 註冊**（ADR-002 2.1、overview.md 3.1）：router 宣告為 `APIRouter(prefix=..., route_class=LimitedFormRoute)`（prefix 只宣告在 router 上、不得再 `include_router` 其他 router，T-001 最終複審 NB-1 / NB-2），並**加入 `app/routers/__init__.py` 的 `ALL_ROUTERS`**（`create_app` 只從此清單掛載，未加入即不會被掛載）。
- [ ] **POST 路徑登錄**：把 `/login`、`/logout` 加入 `tests/integration/test_route_coverage.py` 的 `EXPECTED_POST_PATHS`（T-023 建立；路徑以 routes.md 為準），並確認該測試的「每個 `APIRoute` 都是 `LimitedFormRoute`」「POST 不帶 Token → 403」通過。
- [ ] 整合測試（`TestClient`）：US-013 AC1、AC2、AC5～AC8、AC10、AC11 的主要與負面路徑，含：`GET /login` 後 `user_sessions` 筆數為 0；登入成功回應刪除 nonce Cookie 並設定 Session Cookie；未先 GET 直接 POST /login → 403（`no_nonce`）；連續兩次 `GET /login` 皆有 `Set-Cookie` 且 nonce 值不變；首頁選單不含「我的申請」「待審核」連結；登入表單沒有 `enctype="multipart/form-data"`；未登入 / 逾時 POST /logout → 403；51 字帳號回填為前 50 字；`is_safe_next` 各種惡意值（`//evil`、`/\evil`、`https://…`、控制字元）退回 `/`。
  - （2026-11-07 routes.md 第 4 版同步） **Open Redirect 負面測試（樣板輸出）**：`GET /login?next=//evil.example`、`next=javascript:alert(1)`、`next=/\evil` 時，回應中 `name="next"` 隱藏欄位的值為 `/`，且回應本體**不含**該原始字串；`POST /login` 失敗重新渲染時亦同；合法值（例如 `/venues/1/availability`）原樣保留於隱藏欄位。

## 技術備註
- 可寫入：`app/templates/`、`app/static/`、`app/routers/web/`、`tests/`。
- 樣板 `auth/login.html`、`home.html`；欄位名稱與屬性依 routes.md 第 4 節（`autocomplete="current-password"`、`maxlength`）；表單為 urlencoded（不得用 multipart，routes.md 第 1 節）。
- `ALL_ROUTERS` / `EXPECTED_POST_PATHS` 由 T-023 建立；本 Task 經 T-008 → T-007 → T-023 間接相依，不另列 depends_on。503 頁的 `Retry-After` 由 T-023 handler 統一加上。
- router 一律 `APIRouter(route_class=LimitedFormRoute)`（T-023，ADR-002 2.1）；nonce Cookie 的設定 / 刪除只能經 T-007 的 `set_secure_cookie` / `delete_secure_cookie`。
- router 不匯入 `repositories`；若需要調整 service 介面，回報 Orchestrator 由 backend-developer 處理。
- （2026-11-07 routes.md 第 4 版同步） **Code Review 檢查項**：route 傳給 `TemplateResponse` 的 context 不得含保留名稱 `request`、`current_user`、`csrf_token`、`messages`、`app_timezone`（會被 context processor 覆蓋，routes.md 3.1）；登入前 CSRF Token 改設 `request.state.login_csrf_token`。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（ASVS Level 2）
- [ ] QA 驗收通過（US-013）
- [ ] 文件與 .env.example 已更新
