# 安全日誌事件規格

- 對應 Task：T-003（`security_log` helper、`SecurityEvent` 列舉與欄位白名單）、T-023（`access.denied`、`csrf.failed` 由 handler 記錄）、T-007、T-008、T-009、T-013、T-019（各自記錄事件）、T-021（以 `caplog` 驗證不含敏感資料）
- 依據：AGENTS.md 2.3「日誌」、OWASP Logging Cheat Sheet、ASVS V16（Security Logging）
- 最後更新：2026-11-07（`request_id` 只由伺服器產生，不採用請求標頭；第 1 節補上 `bind_request_context` / `reset_request_context` / `bind_cli_context` 與 CLI 須先呼叫 `configure_logging`）

## 1. 格式與輸出

- Logger 名稱：`security`（一般程式日誌用 `app`）。
- 格式：單行 JSON（`json.dumps(..., ensure_ascii=False)`），UTF-8，輸出到 stderr；部署時由程序管理器收集。Sprint 1 不寫入資料庫。
- 介面（`app/core/logging.py`，T-003；**本節為唯一正式簽章**，其他文件以此為準）：

  ```python
  def security_log(event: SecurityEvent, *, outcome: Literal['success', 'failure'] = 'success', **fields: str | int | bool | None) -> None:
      """記錄安全事件；fields 只接受下表白名單欄位，其他鍵名直接拋 ValueError（開發期即發現誤記錄）。"""
  ```

  `SecurityEvent` 為 `StrEnum`，值即下表事件名稱。
- **自動附加欄位**（由 `RequestIdMiddleware` 以 `contextvars` 設定，service 不必傳遞 Request）：`ts`（UTC ISO 8601）、`request_id`、`client_ip`、`method`、`path`（**不含查詢字串**，避免 `next` 等參數夾帶資料）。CLI 執行時 `request_id` 為 `cli-<uuid>`、`client_ip` 為 `null`、`actor` 為 `cli`。
- **contextvars 設定 helper**（`app/core/logging.py`，T-003 已實作；以下為正式簽章）：

  ```python
  @dataclass(frozen=True, slots=True)
  class RequestContextTokens:            # 還原憑證：request_id、client_ip、method、path 四個 Token[str | None]
      ...

  def bind_request_context(*, request_id: str, client_ip: str | None, method: str, path: str) -> RequestContextTokens: ...
  def reset_request_context(tokens: RequestContextTokens) -> None: ...
  def bind_cli_context() -> str: ...    # request_id = 'cli-<uuid4>'，其餘三欄設為 None；回傳 request_id
  def configure_logging(settings: Settings) -> None: ...   # 設定 app / security logger（stderr、LOG_LEVEL）；可重複呼叫
  ```

  - **HTTP（T-023 `RequestIdMiddleware`）**：每個請求先產生伺服器端 `request_id`，呼叫 `bind_request_context(...)`（`path` 傳 **不含查詢字串**的路徑），並在 `try / finally` 中以 `reset_request_context(tokens)` 還原。同一個 `request_id` 另外由 middleware 自行寫入 `scope['state']['request_id']`（`bind_request_context` 不處理 `scope`，routes.md 3.2）。
  - **CLI（T-009 進入點）**：必須**先**呼叫 `configure_logging(get_settings())`，**再**呼叫 `bind_cli_context()`，之後才可執行任何會呼叫 `security_log` 的動作。未先呼叫 `configure_logging` 時，`security` logger 沒有 handler，INFO 等級的事件（例如 `account.created`）會遺失。`actor='cli'` 仍由呼叫端以欄位傳入。
  - 未設定 contextvars 時（例如單元測試直接呼叫 service），四個自動欄位輸出為 `null`。
- **`request_id` 一律由伺服器隨機產生**（`secrets.token_hex` 或 `uuid.uuid4().hex`，小寫 hex），**不採用**用戶端送來的 `X-Request-ID`、`X-Correlation-ID` 等任何請求標頭，避免攻擊者控制日誌關聯鍵或偽造日誌內容（CWE-117）。同一值也寫入 `scope['state']['request_id']`，供錯誤頁顯示錯誤代碼（routes.md 3.2、error-handling.md 3.4）。
- 日誌字串值一律以 JSON 序列化輸出，換行與控制字元會被跳脫（防 Log Injection，CWE-117）；`username` 另截斷至 50 字。

## 2. 事件清單

| 事件 `event` | 觸發點（Task） | outcome | 欄位（除自動附加欄位外） |
|---|---|---|---|
| `auth.login.success` | `AuthService.authenticate` 成功（T-008） | success | `user_id`、`username`、`role` |
| `auth.login.failure` | 驗證失敗（T-008） | failure | `username`（`normalize_username()` 的結果；格式不合法記 `username=null`、`username_invalid=true`）、`reason`：`unknown_user` / `bad_password` / `inactive` / `locked` / `invalid_format` |
| `auth.login.locked` | 預先記錄的嘗試數達 `LOGIN_MAX_ATTEMPTS` 且該次驗證失敗、鎖定生效（T-008，ADR-005） | failure | `username`、`locked_until`（UTC ISO）、`attempt_count` |
| `auth.login.busy` | 雜湊名額已滿而拒絕登入（503）的**限量彙總**：程序內計數，距上次輸出 ≥ 60 秒才記一筆（T-008，ADR-005 §6） | failure | `rejected_count`（這段期間被拒次數）；**不含** `username`、密碼或任何表單內容（`client_ip` 等自動欄位為觸發輸出的那次請求） |
| `auth.logout` | `POST /logout` 銷毀已登入 Session（T-010） | success | `user_id` |
| `auth.session.expired` | 已登入 Session 因閒置或絕對逾時失效（T-007） | failure | `user_id`、`reason`：`idle` / `absolute` / `user_inactive` |
| `access.denied` | **只由全域 `permission_denied_handler` 記錄**（T-023 實作 handler）；來源為 `require_role` 不符或 service 拋出的 `PermissionDeniedError`（含 `conceal=True` 的資源隱藏）。`require_role` 與 service 本身**不**呼叫 `security_log`，避免重複 | failure | `user_id`、`role`、`reason`（例如 `role_required:staff`、`not_club_manager`、`not_owner`）、`resource`（例如 `club`、`booking_application`）、`resource_id`、`concealed`（bool） |
| `csrf.failed` | `csrf_protect` 或 `/logout` 驗證失敗，由 `csrf_error_handler` 記錄（T-007） | failure | `user_id`（可為 null）、`reason`：`missing` / `mismatch` / `no_session`（登出時無有效 Session）/ `no_nonce`（未登入且無登入前 nonce）/ `expired` / `bad_format` |
| `closed_period.created` | 新增不開放期間（T-013） | success | `actor_id`、`closed_period_id`、`start_date`、`end_date`、`reason_type`、`affected_count` |
| `closed_period.updated` | 編輯（T-013） | success | `actor_id`、`closed_period_id`、`start_date`、`end_date`、`reason_type` |
| `closed_period.deleted` | 刪除（T-013） | success | `actor_id`、`closed_period_id`、`start_date`、`end_date`、`reason_type` |
| `booking.created` | 申請建立成功（T-019） | success | `actor_id`、`booking_id`、`club_id`、`venue_id`、`start_at`、`end_at`（UTC ISO）、`status` |
| `account.created` | CLI 建立帳號（T-009） | success | `actor`（`cli`）、`os_user`、`user_id`、`role`、`club_ids`（逗號分隔字串） |
| `club.created` | CLI 建立社團（T-009） | success | `actor`（`cli`）、`os_user`、`club_id` |
| `account.unlocked` | CLI `unlock-user`（T-009）；**不論是否有 throttle 列都記錄** | success | `actor`（`cli`）、`os_user`、`username`、`was_locked`（bool；沒有該列或未鎖定時為 false） |

- `os_user`：CLI 執行時的作業系統帳號（`getpass.getuser()`，取得失敗記 `null`）。**非權威**（可由環境變數 `USER` / `LOGNAME` 偽造），只供追查參考（Security Review NB-6）。
- 欄位白名單（`security_log` 接受的鍵）：`user_id`、`actor_id`、`actor`、`os_user`、`username`、`username_invalid`、`role`、`reason`、`resource`、`resource_id`、`concealed`、`locked_until`、`attempt_count`、`was_locked`、`rejected_count`、`closed_period_id`、`start_date`、`end_date`、`reason_type`、`affected_count`、`booking_id`、`club_id`、`club_ids`、`venue_id`、`start_at`、`end_at`、`status`。新增欄位需經 Security Reviewer 同意並更新本表。

### 2.1 告警規則（Security Review N-3）

Sprint 1 沒有告警系統，以下規則寫入部署 / 維運文件，供日後接上日誌監控時設定：

| 規則 | 條件 | 意義 |
|---|---|---|
| 帳號重複鎖定 | 同一 `username` 在 1 小時內出現 ≥ 2 次 `auth.login.locked` | 持續性猜測密碼或帳號鎖定型 DoS |
| 大量鎖定 | 10 分鐘內 ≥ 5 個不同 `username` 出現 `auth.login.locked` | 撞庫 / 密碼噴灑攻擊 |
| 權限探測 | 同一 `user_id` 在 10 分鐘內 ≥ 10 次 `access.denied` | 帳號被濫用或 IDOR 探測 |
| 登入忙碌 | 10 分鐘內 `auth.login.busy` 的 `rejected_count` 合計 ≥ 50，或連續 3 個 60 秒區間都有輸出 | 登入洪水攻擊或雜湊名額設定過低；檢查反向代理 IP 頻率限制與 `PASSWORD_HASH_CONCURRENCY` |
| CSRF 異常 | 10 分鐘內 ≥ 20 次 `csrf.failed`（`mismatch` / `bad_format`） | 可能的 CSRF 攻擊嘗試 |
- 申請被商業規則拒絕（R-01、R-13、重疊等）**不是**安全事件，不記錄於 `security`（可於 `app` logger DEBUG）。權限類拒絕（AC3、AC4）才記 `access.denied`。

## 3. 禁止記錄的資料

| 類別 | 欄位 / 內容 |
|---|---|
| 認證秘密 | 密碼（含錯誤的密碼）、`password_hash`、`SECRET_KEY` |
| Session / Token | Session token、`id_hash`、`csrf_token`、登入前 CSRF Token 與 nonce、`Cookie` / `Set-Cookie` 標頭、`Authorization` 標頭 |
| 個資 | `display_name`（姓名）、`email`；**`username`（學號 / 職員編號）只在認證事件記錄**，其他事件一律用 `user_id` |
| 使用者內容 | `activity_description`、`activity_name`、不開放期間 `description`、任何完整表單內容或 request body |
| 其他 | 查詢字串（`path` 不含 query）、完整 `User-Agent`（Sprint 1 不記錄） |

> 已知風險：使用者誤把密碼輸入帳號欄時，若格式合法會以 `username` 被記錄。此為 OWASP 建議中可接受的殘餘風險；緩解為日誌存取權限控管與保存期限（部署文件另定）。

## 4. 測試要求（T-021、各 Task）

- 以 `caplog` 擷取 `security` logger，斷言事件名稱與必要欄位存在。
- 負面斷言：整段日誌文字不含測試用密碼、Session Cookie 值、CSRF Token 值、`display_name`、`activity_description`。
- `security_log` 傳入非白名單鍵時拋 `ValueError`（單元測試）。
