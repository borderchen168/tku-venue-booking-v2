---
id: T-003
title: 專案骨架：FastAPI app、設定、日誌、例外類別與時間工具
story: [US-013, US-001, US-017, US-002, US-004]
status: done        # todo / in-progress / review / done / blocked
assignee: backend-developer
branch: feature/T-003-app-skeleton-config
sprint: sprint-01
depends_on: [T-001]
created: 2026-11-06
---

# T-003 專案骨架：FastAPI app、設定、日誌、例外類別與時間工具

## 說明
建立可啟動的 FastAPI 應用程式與**不涉及 HTTP 請求處理鏈**的共用基礎設施：相依套件與 lock 檔、`Settings` 設定與驗證、日誌與安全日誌 helper、
全部例外類別、Clock 與時間轉換工具、`to_field_errors`、Jinja2 環境，以及測試基礎（conftest / fixtures）。
本 Task 是 overview.md 3.1 多個共用型別的**負責 Task**（`Settings`、`security_log`、全部例外、`Clock`、`timeutils`、`to_field_errors`、templating），後續平行 Task 依其簽章開發，簽章需完全依設計文件建立。

> **2026-11-06 拆分**（T-001 第 3 版同步）：原 T-003 的「HTTP 安全中介層、表單限制與統一錯誤處理」（`app/core/middleware.py`、`app/core/forms.py`、`app/core/error_handlers.py`）移到 **T-023**。
> 設計文件（overview.md 3.1 / 3.2、error-handling.md、ADR-002 2.1）中標示「T-003」的上述三個模組，一律由 T-023 負責；其餘仍由本 Task 負責。

## 完成條件
- [x] **相依套件**（overview.md 第 9 節）：新增執行期相依 `tzdata`；`sqlalchemy>=2.0,<2.2`；**`fastapi>=0.162,<0.163`**（鎖定 minor：T-023 的 `LimitedFormRoute` 與 route 覆蓋測試依賴 0.162 的 routing 行為，升級須先重跑 T-023 測試，overview.md 第 9 節）；確認無其他用途後移除 `itsdangerous`；以 pip-tools 產生 `requirements.lock`、`requirements-dev.lock` 並提交；`python -m pip_audit -r requirements.lock` 無已知漏洞。
- [x] **pytest 設定**：`[tool.pytest.ini_options] filterwarnings = ['error::sqlalchemy.exc.SAWarning']`（overview.md 第 9 節）。
- [x] `app/core/config.py`：`Settings` 實作 overview.md 第 4 節**全部欄位與驗證**，包含：
  - `APP_ENV` 白名單；各數值範圍（`DATABASE_BUSY_TIMEOUT_MS`、`MAX_REQUEST_BODY_BYTES`、`LOGIN_CSRF_MAX_AGE_SECONDS`、`LOGIN_MAX_ATTEMPTS`、`PASSWORD_HASH_CONCURRENCY`）；`SESSION_ABSOLUTE_MAX_AGE_SECONDS ≥ SESSION_MAX_AGE_SECONDS`；`APP_TIMEZONE` 可被 `ZoneInfo` 載入；`DATABASE_URL` 只接受 `sqlite:///`（相對路徑以專案根目錄解析）。
  - production 啟動失敗條件：`APP_DEBUG=true`；`SECRET_KEY` 長度 < 32 **或屬於 `FORBIDDEN_SECRET_KEYS`**（模組常數，至少含 `change-me` 與 `.env.example` 的 `SECRET_KEY` 範例值，ADR-002 4.4）；`SESSION_COOKIE_NAME` 未以 `__Host-` 開頭；`SESSION_COOKIE_SECURE=false`；`ALLOWED_HOSTS` 為空或含 `*`。
  - **不論環境**：`SESSION_COOKIE_NAME` 以 `__Host-` 開頭時 `SESSION_COOKIE_SECURE` 必須為 true，否則啟動失敗（overview.md 第 4 節、ADR-002 4.5）。
- [x] `.env.example` 新增 `DATABASE_BUSY_TIMEOUT_MS`、`SESSION_ABSOLUTE_MAX_AGE_SECONDS`、`LOGIN_CSRF_MAX_AGE_SECONDS`、`PASSWORD_HASH_CONCURRENCY`、`ALLOWED_HOSTS`、`MAX_REQUEST_BODY_BYTES`（範例值），並以註解說明 `SECRET_KEY` 用途（經 `derive_key('login-csrf')` 衍生登入前 CSRF 金鑰、以 `secrets.token_urlsafe(64)` 產生、更換影響，ADR-002 4.4）與 `PASSWORD_HASH_CONCURRENCY` 的記憶體峰值（overview.md 第 7 節）。
- [x] `app/core/logging.py`：`security_log`、`SecurityEvent` 依 security-logging.md 第 1、2 節（唯一正式簽章、單行 JSON、欄位白名單含 `os_user` 與 **`rejected_count`**，非白名單鍵拋 `ValueError`、`username` 截斷 50 字）；`SecurityEvent` 含第 2 節全部事件，**包括 `auth.login.busy`**（由 T-008 觸發）；自動附加欄位所需的 `contextvars`（`request_id`、`client_ip`、`method`、`path`）定義於本模組，**由 T-023 的 `RequestIdMiddleware` 設定**，未設定時為 `null`；CLI 時 `request_id=cli-<uuid>`。
- [x] `app/core/exceptions.py`：error-handling.md 第 2 節**全部**例外類別（`DomainError`、`NotFoundError`、`PermissionDeniedError`、`FieldErrors`、`BusinessRuleError`、`BookingConflictError`、`ServiceBusyError`、`CSRFError`、`LoginRequired`），簽章依設計；`CSRFError.reason` 為 `Literal['missing', 'mismatch', 'no_session', 'no_nonce', 'expired', 'bad_format']`。
- [x] `app/core/clock.py`（`Clock`、`SystemClock`、`get_clock`，overview.md 2.1）與 `tests/fixtures/` 的 `FixedClock` / `fixed_clock` fixture。
- [x] `app/core/timeutils.py`：`local_to_utc`、`utc_to_local`、`local_day_bounds_utc`（ADR-004 第 3 節），含單元測試（naive 輸入拋錯、日界轉換）。
- [x] `app/schemas/_errors.py`：`to_field_errors(exc, labels)`，只依 `loc` 與 `type` 產生繁體中文訊息，**不輸出 `input`、`ctx` 原始值**（error-handling.md 第 2 節）；單元測試驗證輸出不含輸入值。
- [x] `app/core/templating.py`：`Jinja2Templates` autoescape 開啟；context processor **一律以 `getattr(request.state, 'current_user', None)`、`getattr(request.state, 'session', None)` 取值，缺少時視為未登入**（error-handling.md 3.2；實際值由 T-007、T-008 填入）；列舉中文標籤與時間 filter（routes.md 第 3 節）。
- [x] `app/main.py`：`create_app(settings: Settings | None = None)`、`FastAPI(docs_url=None, redoc_url=None, openapi_url=None)`、掛載 `app/static/`、router 掛載點、`GET /healthz`（`200 text/plain` `ok`，routes.md 2.1）。middleware、exception handler 與 `route_class` 的掛載點保留給 T-023。
- [x] 部署 / 啟動說明註明 Uvicorn 使用 `--no-server-header`（overview.md 第 7 節）。
- [x] `tests/conftest.py` 與 `tests/fixtures/`：`settings`（`APP_ENV=test`、`ALLOWED_HOSTS=testserver`、`tmp_path`）、`client` fixture（fixture 分檔，降低平行 Task 衝突，planning.md R7）。
- [x] 測試：
  - 設定驗證：上列每個 production 失敗條件各一；`__Host-` 名稱搭配 `SESSION_COOKIE_SECURE=false` 在 development 也啟動失敗；各數值範圍邊界。
  - **解析 `.env.example` 的 `SECRET_KEY` 值，斷言它在 `FORBIDDEN_SECRET_KEYS` 中**（範例值變更時提醒同步，ADR-002 4.4；以 `pathlib.Path` 定位、`encoding='utf-8'` 讀取）。
  - `security_log` 非白名單鍵拋 `ValueError`、輸出為單行 JSON、控制字元被跳脫；`auth.login.busy` 搭配 `rejected_count` 可正常輸出。
  - context processor 在 `request.state` 沒有 `current_user` / `session` 屬性時不出錯並視為未登入。
  - `/docs`、`/redoc`、`/openapi.json` 回 404；`/healthz` 回 200。

## 技術備註
- 跨平台：路徑一律 `pathlib.Path`（以 `Path(__file__).resolve().parent` 定位 templates/static），`open()` 指定 `encoding='utf-8'`。
- 不實作 Session、CSRF（T-007）、DB（T-004）與 HTTP 中介層 / 錯誤 handler（T-023）；`CSRFError`、`LoginRequired` 類別在本 Task 建立，handler 由 T-023、觸發點由 T-007、T-008 實作。
- `datetime` 匯入慣例為 `import datetime as dt`（overview.md 2.1）。
- 本 Task 完成後 T-004、T-014、T-023 可同時開始（planning.md 波次 2）。
- 可與 T-002 平行進行。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|
| 2026-11-07 | Code Reviewer | 通過（第 1 輪） | 無 blocking；M-1 model 層級錯誤訊息、M-2「日期日期」重複、minor 5 項、nit 7 項已修；7 項自行決定（allowed-confusables、N818 ignore-names、排除 *.md、httpx2、延遲建立 app、未知 loc 歸 `__all__`、DATABASE_URL 限制）皆同意 |
| 2026-11-07 | Security Reviewer | 通過（第 1 輪） | 無 blocking；httpx2 確認為正當套件（Starlette 1.10 TestClient 指定）；lock 檔 hash、SECRET_KEY 熵檢查、bidi 跳脫、app logger 跳脫、ALLOWED_HOSTS 萬用字元 5 項建議已修 |
| 2026-11-07 | Code Reviewer | 通過（第 2 輪） | 無 blocking；major：SECRET_KEY 不同字元數門檻誤擋 hex 金鑰 → 降為 10；minor/nit 4 項已列入修正 |
| 2026-11-07 | Security Reviewer | 通過（第 2 輪） | 無 blocking；Info 4 項（errors() 帶 input、Cs 類別、部署安裝指令、AGENTS.md 修改需核准）已列入修正；AGENTS.md §4 修改由 Orchestrator 核准（使用者已指示建議項目一併修正） |
| 2026-11-07 | QA | 不通過（第 1 輪） | 功能全數符合；AGENTS.md §4 缺 `--no-server-header`、審查紀錄未填、alembic 指令需加註、補 4 個測試 |
| 2026-11-07 | QA | 通過（第 2 輪） | DoD 指令全過（223 passed、branch coverage 100%、pip_audit 無漏洞）；uvicorn 實測 /healthz 200、無 Server 標頭、docs 404 |

## DoD(完成定義)
- [x] ruff check / ruff format --check / mypy 通過
- [x] pytest 通過，branch coverage ≥ 80%
- [x] Code Review 通過
- [x] Security Review 通過（設定驗證、秘密管理、日誌欄位）
- [x] QA 驗收通過
- [x] 文件與 .env.example 已更新
