---
id: T-023
title: HTTP 安全中介層、表單限制與統一錯誤處理
story: [US-013, US-001, US-017, US-002, US-004]
status: todo        # todo / in-progress / review / done / blocked
assignee: backend-developer
branch: feature/T-023-http-security-middleware-errors
sprint: sprint-01
depends_on: [T-003]
created: 2026-11-06
---

# T-023 HTTP 安全中介層、表單限制與統一錯誤處理

## 說明
自 T-003 拆出（2026-11-06，T-001 第 3 版同步，planning.md R11）。建立所有請求共用的 HTTP 安全層：純 ASGI middleware（安全標頭、request id、Host 白名單、
請求本體大小限制、表單 Content-Type 白名單）、表單欄位數上限（`LimitedFormRequest` / `LimitedFormRoute`），以及全域 exception handler 與錯誤頁呈現規則。
本 Task 是 overview.md 3.1 中 `apply_security_headers`、各 middleware、`BodyTooLargeAfterResponseStart`、`LimitedFormRequest`、`LimitedFormRoute`、`FORM_MAX_FIELDS`、`SAFE_METHODS`、
`ALL_ROUTERS`（建立空清單與掛載迴圈）、`register_exception_handlers`，以及 route 覆蓋測試 helper `iter_api_routes` 與 `tests/integration/test_route_coverage.py` 的**負責 Task**
（overview.md 3.1 第 4 版已標示為 T-023）。T-007 的 `ServerSessionMiddleware` 與 `csrf_protect` 建立在本 Task 之上；T-010、T-012、T-015、T-017、T-020 把各自 router 加入 `ALL_ROUTERS`。

> **2026-11-06 第 4 版同步**：新增 `ALL_ROUTERS` 與不依賴 FastAPI 內部的 route 覆蓋測試（ADR-002 2.1 第 3 點）、重複 `Content-Type` → 400、`SAFE_METHODS` 共用常數、
> `BodyTooLargeAfterResponseStart`、503 `Retry-After`、exception handler 不得讀取本體（error-handling.md 第 4 版）。

## 完成條件
- [ ] `app/core/middleware.py`（全部純 ASGI，不用 `BaseHTTPMiddleware`）：
  - `apply_security_headers(response, *, settings, path)` 與 `SecurityHeadersMiddleware`：依 overview.md 第 8 節（單一來源）——CSP 全文（不允許 `data:`、`'unsafe-inline'`）、`nosniff`、`DENY`、`Referrer-Policy`；**所有非 `/static/` 回應 `Cache-Control: no-store`**；production 加 `Strict-Transport-Security`。
  - `RequestIdMiddleware`：設定 T-003 `app/core/logging.py` 的 `contextvars`（`request_id`、`client_ip`、`method`、`path` 不含查詢字串），security-logging.md 第 1 節。
  - `TrustedHostMiddleware`（依 `ALLOWED_HOSTS`）。
  - `BodySizeLimitMiddleware`，依 error-handling.md 3.1：`Content-Length` 非整數或負數 → 400；宣告值 > `MAX_REQUEST_BODY_BYTES` → 413（不讀本體）；其餘（含 chunked）包裝 `receive` 累計，超過上限**拋 `starlette.exceptions.HTTPException(status_code=413)`**（不可拋自訂例外，否則被 FastAPI 表單解析轉成 400）；以 `send` wrapper 記錄是否已送出 `http.response.start`，**回應已開始時改拋專用的 `BodyTooLargeAfterResponseStart`（`RuntimeError` 子類別，定義在本模組、不放 `exceptions.py`）讓 Uvicorn 中止連線**；拋出前只記錄**一筆** `app` WARNING（固定字串 `request body exceeded limit after response started` ＋ `request_id`，不含本體、標頭或使用者資料），error-handling.md 3.1。
  - `FormContentTypeMiddleware`（位於 `BodySizeLimitMiddleware` 之內）：適用範圍為 `method not in SAFE_METHODS`（從 `app/core/forms.py` 匯入，與 T-007 `csrf_protect` 共用）；ASGI `headers` 中**出現多於一個 `content-type` 標頭 → 400**（純文字，不猜測哪一個有效）；單一值以 `python_multipart.multipart.parse_options_header` 解析，主類型不分大小寫、忽略 `charset` 等參數，必須是 `application/x-www-form-urlencoded`，否則 415；本體為空（`Content-Length: 0`，或無 `Content-Length` 也無 `Transfer-Encoding`）時允許無 `Content-Type`（ADR-002 2.1 第 1 點）。
  - **路由前錯誤（TrustedHost 400、`Content-Length` 400 / 413、重複 `Content-Type` 400、415）一律回純文字**（`text/plain; charset=utf-8`，一句中文），不渲染樣板，但仍經 `SecurityHeadersMiddleware`（error-handling.md 3.2）。
- [ ] `create_app` 掛載 middleware，順序依 overview.md 第 2 節（外→內）：**SecurityHeaders → RequestId → TrustedHost → BodySizeLimit → FormContentType →（ServerSession，由 T-007 加入）**；Starlette `add_middleware` 後加者在外層，須以相反順序加入，並在程式註解保留 ServerSession 的插入位置。
- [ ] `app/core/forms.py`：`FORM_MAX_FIELDS: Final = 50`、**`SAFE_METHODS: Final = frozenset({'GET', 'HEAD', 'OPTIONS', 'TRACE'})`（唯一定義，`FormContentTypeMiddleware` 與 T-007 `csrf_protect` 共用）**、`LimitedFormRequest`（覆寫 `form()`，不論呼叫端參數一律 `max_files=0`、`max_fields=FORM_MAX_FIELDS`）、`LimitedFormRoute`（ADR-002 2.1 程式骨架）。
  - `create_app` **第一步**設定 `app.router.route_class = LimitedFormRoute`（只影響 `@app.get` / `@app.post` 直接註冊的 route，如 `/healthz`，必須在其之前設定）。
  - `include_router` **不會**把父層 route_class 套用到子 router；文件註明之後每個子 router 都必須自行宣告 `APIRouter(route_class=LimitedFormRoute)`（ADR-002 2.1 route_class 套用規則）。
- [ ] `app/routers/__init__.py`：`ALL_ROUTERS: Final[tuple[APIRouter, ...]] = ()`（本 Task 建立**空清單**）；`create_app` 以迴圈 `for router in ALL_ROUTERS: app.include_router(router)` 掛載，**不得在其他地方 `include_router`**（ADR-002 2.1、overview.md 3.1 / 3.2）。T-010、T-012、T-015、T-017、T-020 實作時把各自 router 加入清單。
  - **T-001 最終複審 NB-1**：`ALL_ROUTERS` 中的 router **不得再 `include_router`**（禁止巢狀子 router），所有 route 必須直接定義在清單中的 router 上。
  - **T-001 最終複審 NB-2**：prefix 一律宣告在 `APIRouter(prefix=..., route_class=LimitedFormRoute)`；`create_app` 以 `app.include_router(r)` 掛載、**不帶 `prefix` 等參數**，使 router `.routes` 的路徑即為實際對外路徑（覆蓋測試以此比對 `EXPECTED_POST_PATHS`）。
- [ ] `app/core/error_handlers.py`：`register_exception_handlers` 依 error-handling.md 第 3、4 節：
  - `StarletteHTTPException`：400（表單解析失敗 / 欄位數超過上限）→ `errors/400.html`；413（chunked）→ `errors/413.html`；**405 改回 404** 使用 `errors/404.html`；其他依狀態碼。
  - `RequestValidationError` → `errors/422.html`，不列出欄位細節與輸入值；日誌只記 `loc`、`type`。
  - `NotFoundError` → 404；`PermissionDeniedError` → 403（`conceal=True` → 404），**由 handler 記錄 `access.denied`**（含 `concealed`）；`CSRFError` → 403 並記錄 `csrf.failed`（`reason` 含 `no_nonce`）；`LoginRequired` → `303 /login?next=...`（`timed_out=True` 時加 `reason=timeout`；POST 不帶 `next`；只用相對路徑，routes.md 第 1 節）；`ServiceBusyError` → `errors/503.html`，**一律帶 `Retry-After`**（error-handling.md 第 3 節 503 列）。
  - **T-001 最終複審 NB-5**：定義共用常數 `RETRY_AFTER_SECONDS: Final = 5`（或等效 helper，例如 `retry_after_headers()`），放在 `app/core/error_handlers.py`；`ServiceBusyError` handler 與各 route 自行重新渲染 503 時（T-020 等）**都必須使用此常數**，不得各自寫死 `5`。
  - **T-001 最終複審 NB-4（分工確認）**：`csrf_error_handler`（`CSRFError` → 403 ＋ `csrf.failed`）由**本 Task 實作**；`CSRFError` 由 T-007 的 `csrf_protect` / `destroy_session` 拋出。
  - `Exception` → `errors/500.html` ＋ `request_id`；以 `apply_security_headers` 補上安全標頭（500 不經自訂 middleware，error-handling.md 3.3）；日誌不輸出區域變數。
  - 錯誤頁樣板渲染失敗（例如 T-002 尚未合併）→ 純文字 fallback。
  - **所有 handler 不得讀取請求本體**：只能使用 `request.state`（`request_id`、`session`、`current_user`）、`request.method`、`request.url.path` 與標頭；禁止 `request.form()`、`request.body()`、`request.json()`、`request.stream()`（error-handling.md 第 4 節「handler 不得讀取請求本體」）。
- [ ] 測試（error-handling.md 3.1～3.3、overview.md 第 8 節）：
  - 正常頁、404、422、500、413（兩種）、415、TrustedHost 400 回應皆含 overview.md 第 8 節標頭；**503 另含 `Retry-After`，值等於 `RETRY_AFTER_SECONDS`**；`/static/css/main.css` 不含 `no-store`。
  - 65 KiB 本體：有 `Content-Length` → 413 **純文字**且帶安全標頭；**chunked → 413 且為 `errors/413.html`（斷言不是 400）**；`Content-Length: abc` → 400。
  - 測試用 POST route（含 `Form()` 參數）：送 51 個欄位 → 400（`errors/400.html`）；`multipart/form-data`（含 / 不含檔案）、`application/json`、`text/plain` → 415 **純文字**；**兩個 `Content-Type` 標頭 → 400 純文字**；`Content-Type: Application/X-WWW-Form-Urlencoded; charset=utf-8` 通過；空本體無 `Content-Type` 不被 415 擋下。
  - **route 覆蓋測試（ADR-002 2.1 第 3 點，不依賴 FastAPI 內部結構）**：
    - helper `iter_api_routes(app, routers=ALL_ROUTERS) -> Iterator[APIRoute]` 放在 `tests/fixtures/`：走訪 **`app.router.routes` ＋ `ALL_ROUTERS` 各 router 的 `.routes`**（**不是** `app.routes`——FastAPI 0.162 以 `include_router` 掛載的 route 不會直接列在其中）。
    - **T-001 最終複審 NB-1**：`iter_api_routes` 遇到 router `.routes` 中**任何非 `APIRoute` 的項目（含巢狀 include 產生的物件、`Mount` 等）直接失敗**（`AssertionError` 或 `TypeError`，訊息指出該 router），不得略過。
    - `tests/integration/test_route_coverage.py`（**T-001 最終複審 NB-4：本 Task 建立、T-021 驗收；`EXPECTED_POST_PATHS` 最終清單相等由 T-022 驗收**）：每個 `APIRoute` 都是 `LimitedFormRoute`；每個接受 POST 的 route（路徑參數以 `1` 代入）不帶 Token → 403（`csrf_protect` 由 T-007 加入；本 Task 合併時 `ALL_ROUTERS` 為空、沒有 POST route，此參數化測試沒有案例，T-007 起生效）；收集到的 POST 路徑**包含** `EXPECTED_POST_PATHS`（模組常數，**本 Task 起始為空**，由 T-010 / T-015 / T-020 擴充，T-022 驗收最終清單）。
    - **helper 自我驗證（測試用 app）**：建一個子 router **故意不設** `route_class`、以 `include_router` 掛載，斷言 `iter_api_routes` 走訪得到該 route，且「每個 route 都是 `LimitedFormRoute`」的檢查會因它而失敗（抓出忘了設 route_class 的子 router）；另斷言 `include_router` 掛載的 route 確實被走訪到（避免走訪零個 route 時悄悄通過）；**加「巢狀子 router」案例**：清單中的 router 再 `include_router` 另一個 router，`iter_api_routes` 必須判定失敗（T-001 最終複審 NB-1）。
  - 回應已開始後才超過本體上限：以假 ASGI app 先送 `http.response.start` 再讀取超量本體，斷言拋出 **`BodyTooLargeAfterResponseStart`**，且 `caplog` **只有一筆** middleware WARNING、不含本體內容（error-handling.md 3.1）。
  - 在 ServerSession 載入之前觸發的 500（`request.state` 無 `session` / `current_user`）仍能渲染 `errors/500.html` 且不出錯（error-handling.md 3.2）。
  - 405 回 404：以 `DELETE` 呼叫只接受 GET 的 route，**不帶本體**送出（帶本體會先被 `FormContentTypeMiddleware` 以 415 擋下，測不到 405 處理，error-handling.md 第 5 節）；不在白名單的 Host 回 400；500 時本體不含 stack trace 與例外類別名稱；`PermissionDeniedError` 觸發 `access.denied`、`conceal=True` 回 404；`CSRFError` 觸發 `csrf.failed`。

## 技術備註
- 依賴 T-003 的 `Settings`、`exceptions`、`security_log`、`templating`；不實作 Session / CSRF（T-007）。
- **版本鎖定**：`LimitedFormRequest` / `LimitedFormRoute`、route 走訪方式與 `include_router` 不套用父層 route_class 的行為，已在 FastAPI 0.162.0 / Starlette 1.10.0 / Uvicorn 0.54.0 實測；T-003 將 `fastapi` 鎖為 `>=0.162,<0.163`。日後升級須先重跑本 Task 的表單上限與 route 覆蓋測試（overview.md 第 9 節）。
- 新增 router 必須加入 `ALL_ROUTERS`、新增 POST route 必須擴充 `EXPECTED_POST_PATHS`。`ALL_ROUTERS` 由本 Task 建立，所有 web Task 都相依本 Task：T-012 直接相依；T-010 / T-015 / T-020 經 T-008 → T-007、T-017 經 T-012 間接相依（皆已在較晚波次）。
- 錯誤頁樣板（`errors/400.html`、`413.html`、`503.html` 等）由 T-002 提供；**415 不需要樣板**（純文字）。兩者可平行，未合併前以純文字 fallback 測試。
- T-007 測試「帶 `Form()` 參數的 route」時沿用本 Task 的 `LimitedFormRoute`；T-021 再以實際 route 驗證。
- 本 Task 不在關鍵路徑上（與 T-004、T-014 同在波次 2，須於 T-007 開始前合併；可容許延誤至 T-005 合併為止），見 planning.md。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（安全標頭、請求大小與表單限制、錯誤處理不洩漏細節）
- [ ] QA 驗收通過
- [ ] 文件與 .env.example 已更新
