---
id: T-007
title: Server-side Session 與 CSRF 機制
story: US-013
status: todo        # todo / in-progress / review / done / blocked
assignee: backend-developer
branch: feature/T-007-session-csrf
sprint: sprint-01
depends_on: [T-003, T-005, T-023]
created: 2026-11-06
---

# T-007 Server-side Session 與 CSRF 機制

## 說明
依 ADR-001、ADR-002（第 3 版）實作**只存已登入使用者**的伺服器端 Session，以及 CSRF 防護：已登入使用 Synchronizer Token(同步權杖)，
**登入前使用無狀態 HMAC Token ＋ nonce Cookie（不建立匿名 Session、不寫 DB）**。作為登入（US-013）與所有會改變狀態之表單（US-017、US-004）的共用安全機制。
本 Task 是 `CurrentUser`、`ServerSession`、`SessionStore`、`csrf_protect`、`set_secure_cookie` / `delete_secure_cookie`、`derive_key` 等型別的負責 Task（overview.md 3.1）。
表單解析限制（Content-Type 白名單、`LimitedFormRoute` 欄位上限）由 T-023 提供，本 Task 不重做。

## 完成條件
- [ ] `app/core/identity.py`：`CurrentUser`（frozen dataclass：`id`、`username`、`display_name`、`role`；`is_staff` / `is_student`），overview.md 3.1。
- [ ] `app/core/cookies.py`：`set_secure_cookie(response, name, value, *, max_age, settings)`、`delete_secure_cookie(response, name, *, settings)`（ADR-002 4.5）：一律 `HttpOnly`、`SameSite=Lax`、`Path=/`、`Secure=settings.SESSION_COOKIE_SECURE`；刪除時帶**相同屬性**並 `Max-Age=0`。Session Cookie 與 nonce Cookie 的設定 / 刪除**只能**經這兩個函式。
- [ ] `app/core/keys.py`：`KeyPurpose = Literal['login-csrf']`、`derive_key(purpose) -> bytes`（`HMAC-SHA256(SECRET_KEY, b'tku-venue-booking/' + purpose + b'/v1')`，`lru_cache`），ADR-002 4.4；**唯一可對 `SECRET_KEY` 做 HMAC 的模組**。
- [ ] `app/core/session_store.py`：`SessionStore`（`user_sessions` 存取，含 `delete_for_user`、`delete_expired`），每次操作使用自有短生命週期 DB Session；**所有寫入一律 `immediate_transaction`**，讀取為唯讀交易（ADR-001 第 4 節、ADR-003 2.1）。
- [ ] `app/core/session.py`：純 ASGI `ServerSessionMiddleware`（插入 T-023 預留的最內層位置，overview.md 第 2 節：SecurityHeaders → RequestId → TrustedHost → BodySizeLimit → FormContentType → **ServerSession**）與 API `create_session_for_user(request, response, user_id)`、`destroy_session(request, response)`、`add_flash`、`pop_flashes`、`ServerSession`、`FlashMessage`，行為依 ADR-001 第 1～3、6 節：
  - token `secrets.token_urlsafe(32)`、DB 只存 SHA-256；格式不合的 Cookie 不查 DB。
  - Cookie 屬性依 ADR-001 第 2 節（`HttpOnly`、`SameSite=Lax`、`Path=/`、無 `Domain` / `Max-Age`、`Secure` 依設定），經 `set_secure_cookie` / `delete_secure_cookie`。
  - 閒置逾時 `SESSION_MAX_AGE_SECONDS`、絕對逾時 `SESSION_ABSOLUTE_MAX_AGE_SECONDS`、使用者停用即失效，設 `request.state.session_expired` 並記錄 `auth.session.expired`。
  - `last_seen_at` **最多每 60 秒更新一次**。
  - **略過路徑**：`/static/` 開頭與 `/healthz` 不讀 Cookie、不查 DB，`session` / `current_user` 設 `None`、`session_expired=False`（ADR-001 第 6 節）。
  - **`pop_flashes`：已載入的 `ServerSession.data` 沒有 flash 時直接回傳空 list、不開任何交易**；有 flash 才以 `immediate_transaction` 重讀並清空（ADR-001 第 3 節）。`add_flash` 以 `immediate_transaction` 讀改寫。未登入時 `add_flash` no-op、`pop_flashes` 回傳空 list。
  - DB 存取以 `run_in_threadpool` 呼叫，不阻塞 event loop。
- [ ] `app/core/csrf.py`：全域相依 `csrf_protect(request, clock: Clock = Depends(get_clock))`（`FastAPI(dependencies=[Depends(csrf_protect)])`）、`issue_login_csrf_token`、`verify_login_csrf_token`，依 ADR-002 第 2、4 節：
  - 安全方法判斷 **`from app.core.forms import SAFE_METHODS`**（T-023 提供的唯一定義，與 `FormContentTypeMiddleware` 共用），不得自行定義方法清單（ADR-002 第 2 節程式骨架）。
  - 以 `await request.form()` 取得 FastAPI 已解析並快取的表單（欄位數限制由 T-023 `LimitedFormRequest` 保證，**不在此傳 `max_fields`**，ADR-002 2.1）；**Token 只接受表單欄位 `csrf_token`，不接受任何標頭**。
  - 時間一律來自注入的 `Clock`（測試以 `dependency_overrides[get_clock]` 固定）。
  - 已登入以 `hmac.compare_digest` 比對 Session Token。
  - 未登入：nonce Cookie `{SESSION_COOKIE_NAME}_login`（**`SameSite=Lax`**、`Max-Age=LOGIN_CSRF_MAX_AGE_SECONDS`）＋ `v1.<issued_at>.<mac>` Token（`derive_key('login-csrf')`、格式 regex、時效與 60 秒時鐘偏差）。
  - `issue_login_csrf_token`：沿用格式合法的既有 nonce（沒有才產生），**每次都以同一 nonce 重新 `Set-Cookie` 刷新 `Max-Age`**，不更換有效 nonce（ADR-002 4.2）。
  - 失敗拋 `CSRFError(reason=...)`：`missing` / `mismatch` / `no_nonce`（未登入且無或格式不合的 nonce）/ `expired` / `bad_format`；`no_session` 由 `destroy_session` 使用（handler 由 T-023 建立，記錄 `csrf.failed`）。
- [ ] 清理：`SessionStore.delete_expired` 與模組常數 `SESSION_CLEANUP_MIN_INTERVAL_SECONDS = 300`（ADR-001 第 5 節；**呼叫點為 T-008 `AuthService.maybe_cleanup(now)`，在 `reserve_attempt` 之後觸發**，`create_session_for_user` 本身不清理）。
- [ ] context processor 注入 `csrf_token`（已登入取 Session、登入頁取 `request.state.login_csrf_token`）與 `messages`（routes.md 第 3 節；沿用 T-003 的 `getattr` 取值方式）。
- [ ] 測試（含負面測試，ADR-001 第 7 節、ADR-002 全文）：
  - Cookie 屬性；production 設定下 Cookie 名稱為 `__Host-` 前綴、帶 `Secure`，nonce Cookie 名稱同樣沿用前綴且為 `SameSite=Lax`。
  - **`app/core/cookies.py` 設定與刪除兩種情境都要斷言**（ADR-002 4.5 測試要求），Session Cookie 與 nonce Cookie 各測一次：
    - **設定**用的 `Set-Cookie` 含 `HttpOnly`、`SameSite=Lax`、`Path=/`；`SESSION_COOKIE_SECURE=true` 時含 `Secure`、false 時不含；nonce 另含 `Max-Age=<LOGIN_CSRF_MAX_AGE_SECONDS>`，Session 不含 `Max-Age` / `Expires`。
    - **刪除**用的 `Set-Cookie` 含 `Max-Age=0`、`Path=/`、`HttpOnly`、`SameSite=Lax`，`SESSION_COOKIE_SECURE=true` 時含 `Secure`。
  - `derive_key` 不同 purpose 產生不同金鑰、相同 `SECRET_KEY` 結果穩定；更換 `SECRET_KEY` 後舊登入前 Token 失效。
  - `create_session_for_user` 產生新 Session ID 與新 CSRF Token，並刪除請求帶來的舊 Session；`destroy_session` 後舊 Cookie 無效；無有效 Session 時 `destroy_session` 拋 `CSRFError('no_session')`。
  - 閒置 1801 秒必失效、1700 秒必有效；絕對逾時；停用使用者下一個請求即失效；`last_seen_at` 60 秒內不重寫。
  - **無 flash 的已登入頁面渲染不產生寫入交易**（以 `before_cursor_execute` 斷言沒有 `BEGIN IMMEDIATE`）；`/static/*` 與 `/healthz` 不查 `user_sessions`。
  - 匿名請求（含 `GET /login` 發 Token）後 `user_sessions` 筆數為 0。
  - 登入前 Token：缺 nonce（`no_nonce`）、格式錯（`bad_format`）、竄改 mac 或換 nonce（`mismatch`）、過期與未來時間超過 60 秒（`expired`，以 `FixedClock` 推進時間）皆 403；正確組合通過；**連續兩次發 Token 時 nonce 不變且每次都有 `Set-Cookie`**。
  - 已登入：缺少 / 錯誤 Token 403、正確通過；以 `X-CSRF-Token` 等標頭送 Token 仍視為缺少（403）。
  - **以帶 `Form()` 參數的測試 route**（`LimitedFormRoute`）驗證：`csrf_protect` 讀取表單後，endpoint 的 `Form()` 參數取得相同值；送 51 個欄位（帶正確 Token）→ 400；`multipart/form-data` → 415（ADR-002 2.1 第 3 點）。

## 技術備註
- 不使用 Starlette `SessionMiddleware`（ADR-001 選項 A 已否決），也不新增 CSRF / Session 套件。
- 匯入規則：`core/session.py` 透過 `core/session_store.py` 存取 `UserSession` model，**不匯入 `repositories`**（overview.md 第 2 節）。
- 日誌禁止記錄 Session token、`id_hash`、`csrf_token`、nonce（security-logging.md 第 3 節）。
- `SECRET_KEY` 在 Sprint 1 的唯一用途是 `derive_key('login-csrf')`（ADR-002 4.4）；新增 `KeyPurpose` 需經 Security Reviewer 同意。
- 新增相依 T-023（middleware 掛載位置、`LimitedFormRoute`、`SAFE_METHODS`、`CSRFError` handler）。
- T-023 的 `tests/integration/test_route_coverage.py`「每個 POST route 不帶 Token → 403」在本 Task 加入 `csrf_protect` 後才實際生效；本 Task 合併時該測試須維持通過。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（ASVS Level 2：Session 管理 V7、CSRF）
- [ ] QA 驗收通過
- [ ] 文件與 .env.example 已更新
