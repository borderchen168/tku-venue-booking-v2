# 錯誤處理規格

- 對應 Task：T-003（例外類別 `app/core/exceptions.py`、`to_field_errors`、context processor）、**T-023**（middleware、`app/core/forms.py`、`app/core/error_handlers.py`、錯誤頁 fallback、`ALL_ROUTERS` 覆蓋測試）、T-002（錯誤頁樣板）、各 web Task（表單錯誤重新渲染）
- 依據：AGENTS.md 2.3「錯誤處理」（正式環境不回傳 stack trace 或內部錯誤細節）
- 最後更新：2026-11-06（第 4 版：`ALL_ROUTERS` 覆蓋測試、handler 不讀本體、`BodyTooLargeAfterResponseStart`、503 Retry-After、重複 Content-Type 400）

## 1. 原則

1. **service 只拋 domain 例外，不知道 HTTP**；router 或全域 exception handler 負責轉換。
2. **表單類錯誤**（欄位驗證、商業規則、重疊）由 route 捕捉並**重新渲染表單**，保留已填資料；**非表單錯誤**（權限、不存在、CSRF、未預期例外）由全域 handler 渲染統一錯誤頁。
3. 錯誤頁**不顯示**：stack trace、例外類別名稱、SQL、檔案路徑、設定值、套件版本、使用者輸入值。只顯示友善訊息、`request_id`（「錯誤代碼：a1b2c3d4」）與「回首頁」連結。
4. `APP_DEBUG=true` 只允許在非 production 使用（`Settings` 驗證強制）；即使 debug，也不得在頁面顯示請求本體或表單值。
5. 所有錯誤回應帶安全標頭與 `Cache-Control: no-store`（overview.md 第 8 節）。
6. Sprint 1 沒有 JSON API；若未來新增 `/api/*`，相同例外改以 JSON 回應（handler 依路徑前綴分流）。

## 2. 例外類別（定義於 `app/core/exceptions.py`，T-003 建立；`BodyTooLargeAfterResponseStart` 例外地放在 `app/core/middleware.py`，T-023）

```python
class DomainError(Exception):
    """所有 domain 例外的基底；message 為可直接顯示給使用者的繁體中文。"""
    def __init__(self, message: str) -> None: ...

class NotFoundError(DomainError): ...                 # → 404（不記錄 access.denied）

class PermissionDeniedError(DomainError):
    """→ 403；conceal=True 時改以 404 呈現（隱藏資源存在與否）。access.denied 一律由全域 handler 記錄。"""
    def __init__(self, message: str = '您沒有權限執行此操作', *, reason: str,
                 resource: str | None = None, resource_id: int | None = None,
                 conceal: bool = False) -> None: ...

class FieldErrors(DomainError):                       # → 表單 422（逐欄）；也用於查詢參數驗證（週檢視）
    def __init__(self, errors: dict[str, str]) -> None: ...   # 欄位名 → 訊息；'__all__' 為全域

class BusinessRuleError(DomainError):                 # → 表單 422（頂部訊息）
    def __init__(self, code: str, message: str) -> None: ...  # code 供測試斷言

class BookingConflictError(DomainError): ...          # → 表單 409「該時段已被借用」
class ServiceBusyError(DomainError): ...              # → 503「系統忙碌，請稍後再試」＋ Retry-After（SQLite 寫鎖逾時、雜湊名額已滿）

# HTTP 層流程控制（同樣放在 core/exceptions.py，Code Review #4）
class CSRFError(Exception):                           # → 403 CSRF 錯誤頁 + csrf.failed
    def __init__(self, *, reason: Literal['missing', 'mismatch', 'no_session', 'no_nonce', 'expired', 'bad_format']) -> None: ...
    # no_session：/logout 時沒有有效已登入 Session；no_nonce：未登入且沒有（或格式不合的）登入前 nonce Cookie
class LoginRequired(Exception):                       # → 303 /login
    def __init__(self, next_path: str | None, timed_out: bool) -> None: ...
```

- `BusinessRuleError.code` 白名單：`outside_opening_hours`、`closed_date`、`outside_semester`、`apply_deadline_passed`（未來 `club_suspended`、`vacation_closed` 等）。
- **資源隱藏規則（Code Review #9）**：以 id 存取「屬於某人」的資源時：
  - 資源不存在 → `NotFoundError`（不寫 `access.denied`）。
  - 資源存在但非擁有者 → `PermissionDeniedError(reason='not_owner', resource=..., resource_id=..., conceal=True)` → handler 記錄 `access.denied` 並回 **404** 頁。使用者看到的兩者完全相同。
  - 角色不符（`require_role` 或 service 角色檢查）→ `PermissionDeniedError(reason='role_required:<role>')` → 403。
  - US-004 AC3（竄改 `club_id`）依 AC 回 403：`PermissionDeniedError(reason='not_club_manager', resource='club', resource_id=club_id)`。
- Pydantic `ValidationError` 轉 `FieldErrors`：`app/schemas/_errors.py` `to_field_errors(exc: ValidationError, labels: Mapping[str, str]) -> dict[str, str]`。只使用 `loc` 與 `type` 對應到繁體中文訊息，**不得輸出 `input`、`ctx` 中的原始值**（Security Review N-10）。

## 3. HTTP 狀態碼與呈現

| 狀態 | 觸發 | 呈現 | 記錄 |
|---|---|---|---|
| 303 | `LoginRequired`；POST 成功 | 導向（相對路徑） | – |
| 400 | 登入失敗（所有原因相同） | 重新渲染 `auth/login.html` | `auth.login.failure`（security） |
| 400 | 表單解析失敗或欄位數超過 `FORM_MAX_FIELDS`（`LimitedFormRequest` 中 Starlette 拋 `HTTPException(400)`） | `errors/400.html`「請求格式不正確」 | `app` WARNING（不記錄本體） |
| 400 | `Host` 不在 `ALLOWED_HOSTS`（`TrustedHostMiddleware`）；`Content-Length` 非整數或為負數（`BodySizeLimitMiddleware`）；非安全方法帶多個 `Content-Type` 標頭（`FormContentTypeMiddleware`） | **middleware 層純文字**（見 3.2） | `app` WARNING |
| 403 | `PermissionDeniedError`（`conceal=False`） | `errors/403.html`「您沒有權限執行此操作」 | `access.denied`（handler） |
| 403 | `CSRFError` | `errors/403.html`，訊息「表單已失效，請重新整理頁面後再試」 | `csrf.failed`（handler） |
| 404 | `NotFoundError`、`PermissionDeniedError(conceal=True)`、Starlette 404（含 `/api/*`、`/docs`） | `errors/404.html`「找不到您要的頁面」 | conceal 時 `access.denied` |
| 404 | Starlette **405**（Method Not Allowed） | **狀態碼改為 404**，使用 `errors/404.html`（不透露路由存在，Code Review #12） | – |
| 409 | `BookingConflictError` | 重新渲染表單＋頂部訊息 | – |
| 413 | 宣告的 `Content-Length` > `MAX_REQUEST_BODY_BYTES` | **middleware 層純文字**（見 3.2） | `app` WARNING |
| 413 | chunked / 未宣告長度，讀取時累計超過上限（`receive` wrapper 拋 `HTTPException(413)`） | `http_exception_handler` 渲染 `errors/413.html`「送出的資料過大」 | `app` WARNING |
| 415 | 非安全方法的 `Content-Type` 不是 `application/x-www-form-urlencoded`（`FormContentTypeMiddleware`，ADR-002 2.1） | **middleware 層純文字**（見 3.2） | `app` WARNING |
| 422 | `FieldErrors`、`BusinessRuleError` | 重新渲染表單 | – |
| 422 | `RequestValidationError`（路徑參數型別錯，例如 `/venues/abc`） | `errors/422.html`「請求內容格式不正確」；**不列出**欄位細節與輸入值；日誌只記 `loc`、`type`（不記 `input`） | `app` INFO |
| 422 | 週檢視 `week_start` 無效 | 渲染本週借用狀況＋錯誤訊息（routes.md 2.3） | – |
| 500 | 未捕捉的 `Exception` | `errors/500.html`「系統發生錯誤，請稍後再試」＋ `request_id` | `app` ERROR，stack trace 只在伺服器日誌 |
| 503 | `ServiceBusyError` | 表單情境重新渲染＋頂部訊息；非表單情境（含登入時雜湊名額已滿，ADR-005 §6）`errors/503.html`。**一律帶 `Retry-After: 5`**（Security Review NB-E） | `app` WARNING；雜湊名額已滿另記限量彙總的 `auth.login.busy`（security-logging.md） |

### 3.1 請求本體與表單限制（Security Review N-8、Code Review B-1 / M-1，T-023）

**`BodySizeLimitMiddleware`**（純 ASGI，`app/core/middleware.py`）：

1. `Content-Length` 非整數或為負數 → 直接回 400（純文字）。
2. 宣告的 `Content-Length` > `MAX_REQUEST_BODY_BYTES` → 不讀本體，直接回 413（純文字）。
3. 其餘情況（含 chunked、或宣告值偏小）包裝 `receive`，累計已收的 `http.request` 位元組：
   - 超過上限時，wrapper **拋 `starlette.exceptions.HTTPException(status_code=413)`**。不可拋自訂例外：FastAPI 的表單解析（`_get_form`）會把非 `HTTPException` 的例外轉成 400（Code Review M-1 實測）。`HTTPException(413)` 由 `http_exception_handler` 渲染 `errors/413.html`。
   - **下游已開始回應時**（以 `send` wrapper 記錄是否已送出 `http.response.start`）：狀態碼已無法更改，wrapper 改為拋專用的 `BodyTooLargeAfterResponseStart`（`RuntimeError` 子類別，定義在 `app/core/middleware.py`，T-023；屬 middleware 內部細節，不放 `exceptions.py`），讓 ASGI server（Uvicorn）中止連線（Security Review NB-D）。
     - middleware 在拋出前記錄**一筆** `app` WARNING：固定字串 `request body exceeded limit after response started` ＋ `request_id`，**不含**本體、標頭或使用者資料。
     - Uvicorn 仍會以 `uvicorn.error` 記錄一次「Exception in ASGI application」與 traceback。**接受**此行為：traceback 只含框架堆疊與上述固定訊息（例外不帶本體內容），且此情況只會在程式錯誤時出現（Sprint 1 的 route 都在回應前讀完表單），保留 traceback 有助除錯；不另外過濾 Uvicorn 日誌。
     - 測試：以假的 ASGI app 先送 `http.response.start` 再讀取超量本體，斷言拋出 `BodyTooLargeAfterResponseStart`、`caplog` 只有一筆 middleware WARNING 且不含本體內容。

**`FormContentTypeMiddleware`**（純 ASGI，位於 `BodySizeLimitMiddleware` 之內）：非安全方法只接受 `application/x-www-form-urlencoded`，其他回 415；空本體可無 `Content-Type`（ADR-002 2.1）。

**欄位數**：`LimitedFormRequest` 覆寫 `form()`，強制 `max_fields=FORM_MAX_FIELDS`（50）、`max_files=0`；每個子 router 各自宣告 `route_class=LimitedFormRoute`，並且只從 `app/routers/__init__.py` 的 `ALL_ROUTERS` 掛載（`include_router` 不會套用父層的 route_class，ADR-002 2.1）。**不得**依賴在 dependency 中呼叫 `request.form(max_fields=...)`——FastAPI 已在 dependency 執行前以預設限制解析並快取表單。

**測試（T-023；T-007 須涵蓋有 `Form()` 參數的 route）**：

- 65 KiB 本體：有 `Content-Length` → 413 純文字且帶安全標頭；chunked → 413 且為 `errors/413.html`（斷言不是 400）。
- `Content-Length: abc` → 400。
- 對**有 `Form()` 參數**的 POST route 送 51 個欄位（帶正確 Token）→ 400。
- `multipart/form-data`（含 / 不含檔案）、`application/json`、`text/plain` → 415；兩個 `Content-Type` 標頭 → 400；空本體無 `Content-Type` → 403（缺 Token）。
- 走訪 `app.router.routes` ＋ `ALL_ROUTERS` 各 router 的 `.routes`（**不是** `app.routes`），每個 `APIRoute` 都是 `LimitedFormRoute`，且收集到的 POST 路徑包含預期清單（ADR-002 2.1 第 3 點）。

### 3.2 middleware 層回應與樣板 context（Code Review M-2）

- **路由之前**產生的錯誤（TrustedHost 400、`Content-Length` 400 / 413、415）一律回**純文字**（`text/plain; charset=utf-8`，一句中文，例如「送出的資料過大」），不渲染 Jinja2 樣板。理由：此時 Session 尚未載入，且這類請求多半不是一般使用者操作，不值得冒樣板渲染失敗的風險。這些回應仍經最外層的 `SecurityHeadersMiddleware`。
- **經 exception handler** 渲染的錯誤頁（400、403、404、413〔chunked〕、422、500、503）使用樣板；其中 500 在 `ServerErrorMiddleware` 執行，`request.state` 可能缺少 `session` / `current_user`。因此 `app/core/templating.py` 的 context processor **一律以 `getattr(request.state, 'current_user', None)`、`getattr(request.state, 'session', None)` 取值**，缺少時視為未登入（導覽列顯示訪客版）。
- 測試（T-023）：在 ServerSessionMiddleware 之前觸發的 500（例如 monkeypatch 讓 session 載入拋例外）仍能渲染 `errors/500.html` 且不出錯；415 / 413（Content-Length）為純文字且帶安全標頭。

### 3.3 安全標頭與 500

Starlette 把 `Exception`（500）handler 交給最外層的 `ServerErrorMiddleware` 執行，回應**不會經過**使用者自訂 middleware。因此安全標頭邏輯抽成 `apply_security_headers(response, ...)`，由 `SecurityHeadersMiddleware` 與 `unhandled_exception_handler` 共用；T-023 以測試驗證 500 回應仍有 CSP、`no-store` 等標頭。

- 錯誤頁樣板若本身渲染失敗（例如 T-002 尚未合併），handler 退回純文字 fallback（`text/plain; charset=utf-8`，只有狀態碼與一句中文）。
- 500 的日誌只記錄 traceback，不得使用會輸出區域變數的 traceback 格式（例如 `rich` 的 `show_locals`），避免密碼等區域變數進入日誌。

## 4. Handler 註冊（T-023 `app/core/error_handlers.py`）

```python
def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)     # 400 / 404 / 405→404 / 413（chunked）/ 其他
    app.add_exception_handler(RequestValidationError, request_validation_handler) # 422 頁
    app.add_exception_handler(NotFoundError, not_found_handler)                   # 404 頁
    app.add_exception_handler(PermissionDeniedError, permission_denied_handler)   # 403 或 404 頁 + access.denied
    app.add_exception_handler(CSRFError, csrf_error_handler)                      # 403 頁 + csrf.failed
    app.add_exception_handler(LoginRequired, login_required_handler)              # 303
    app.add_exception_handler(ServiceBusyError, service_busy_handler)             # 503 頁
    app.add_exception_handler(Exception, unhandled_exception_handler)             # 500 頁
```

`FieldErrors`、`BusinessRuleError`、`BookingConflictError` 不註冊全域 handler；route 必須自行捕捉並重新渲染（若漏接則落到 500，測試會發現）。

**handler 不得讀取請求本體（Code Review #3）**：所有 exception handler 只能使用 `request.state`（`request_id`、`session`、`current_user`）、`request.method`、`request.url.path` 與標頭；**禁止**呼叫 `request.form()`、`request.body()`、`request.json()`、`request.stream()`。理由：本體可能已被消耗、超量或格式錯誤（再次讀取會觸發另一個例外或繞過大小限制），且可能含密碼。需要重新渲染表單的情況由 route 自行處理（route 已持有解析後的值）。

## 5. 負面測試要求（T-021，Security Review N-10）

- 格式錯誤的登入（例如 51 字帳號＋密碼 `S3cret-Pass!`）：回應本體與 `caplog` 全文皆不含該密碼。
- 500 路徑：以 monkeypatch 讓 `AuthService.authenticate` 拋例外並送出含密碼的登入表單 → 回 500、回應本體不含 stack trace、`caplog` 全文不含密碼與 CSRF Token。
- `/venues/abc`、`/venues/0` 回 422 頁，本體不含輸入值與任何技術細節。
- `DELETE /venues`（405）**不帶本體**送出 → 404（若帶本體，會先被 `FormContentTypeMiddleware` 以 415 擋下，測不到 405 的處理）。
- 503 回應含 `Retry-After` 標頭。
