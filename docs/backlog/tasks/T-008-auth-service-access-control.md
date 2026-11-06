---
id: T-008
title: 認證服務與存取控制相依
story: US-013
status: todo        # todo / in-progress / review / done / blocked
assignee: backend-developer
branch: feature/T-008-auth-service-access-control
sprint: sprint-01
depends_on: [T-005, T-007]
created: 2026-11-06
---

# T-008 認證服務與存取控制相依

## 說明
依 ADR-005（第 4 版）實作密碼雜湊（含**不等待**的併發上限與名額已滿的彙總記錄）、帳號正規化、帳號驗證、「**先記錄嘗試再驗證**」的登入鎖定與安全日誌、單一入口的資料清理（`maybe_cleanup`），
以及 route 共用的身分與角色檢查相依函式（預設拒絕）。

## 完成條件
- [ ] `app/core/security.py`（ADR-005 第 2.1、6 節）：
  - **`normalize_username(raw) -> str | None`**：`strip → lower → re.fullmatch(r'[a-z0-9._-]{1,50}')`，不符回傳 `None`；為帳號正規化的**唯一入口**（`AuthService`、`login_throttles` 鍵、`UserRepository.get_by_username`、T-009 `AccountService` / CLI 皆使用，不得另寫 `.lower()` 或 regex）。
  - `PasswordService`：argon2id `RFC_9106_LOW_MEMORY` 參數、`hash` / `verify` / `dummy_verify` / `needs_rehash`；持有 `threading.BoundedSemaphore(PASSWORD_HASH_CONCURRENCY)`，**簽章 `slot(self, *, blocking: bool = False) -> Iterator[None]`（`@contextmanager`，`blocking` 為 keyword-only）**：預設不等待，取不到立即拋 `ServiceBusyError`；`blocking=True` 只供 CLI（T-009）使用（ADR-005 第 6 節）；`hash` / `verify` / `dummy_verify` 未持有名額時（`threading.local` 旗標）拋 `RuntimeError`。
  - **名額已滿的彙總記錄**（ADR-005 第 6 節、security-logging.md 第 2 節）：被拒時程序內計數 +1（以 `threading.Lock` 保護，只在被拒路徑上）；以 `HASH_BUSY_LOG_INTERVAL_SECONDS = 60` 彙總輸出 `auth.login.busy`；**不含** `username`、密碼或任何表單內容。503 的 `Retry-After` 由 T-023 的 `ServiceBusyError` handler 以 `RETRY_AFTER_SECONDS` 加上。
  - **彙總規則（T-001 最終複審 NB-3，以此為準）**：**第一次被拒立即輸出**（`rejected_count=1`）；之後被拒只累計；下一次在**距上次輸出 ≥ 60 秒後被拒時**輸出累計數（含該次），然後歸零並更新輸出時間。程式註解須註明：攻擊停止後，最後一段累計要等下一次被拒才會輸出（不另設排程器）。
  - `validate_password_policy(password, username)`（cli.md 第 2 節規則）。
- [ ] `app/core/data/common_passwords.txt`：常見密碼清單（UTF-8、每行一筆、小寫比對，保留授權說明，overview.md 3.2）。
- [ ] `app/repositories/user_repository.py`（`get_by_username`〔只接受已正規化的值〕、`get_by_id`、`add`）與 `app/repositories/login_throttle_repository.py`（`reserve_attempt`、`reset`、`delete_stale`），`reserve_attempt` 依 ADR-005 第 1 節五個步驟在**單一 `immediate_transaction`** 中執行，並在 argon2 驗證**之前** commit。
- [ ] `app/services/auth_service.py` `AuthService.authenticate(username, password, now) -> CurrentUser | None`，流程依 ADR-005 第 2 節流程圖：
  - **整個流程包在 `with passwords.slot():` 內：先取得雜湊名額，才 `normalize_username` 與 `reserve_attempt`**；名額已滿 → `ServiceBusyError`（503），**不寫入、不變更 `login_throttles`**。
  - 帳號以 `normalize_username` 驗證、密碼長度 1～128 在 service 內驗證，**不使用 Pydantic schema**（避免 FastAPI 422 造成不同回應，ADR-005 第 3 節）；格式不符不寫 throttle。
  - 每次嘗試恰執行一次 argon2（真實驗證或 `dummy_verify`）；停用帳號在密碼驗證之後判斷。
  - 成功：同一 `immediate_transaction` 內 `reset` throttle；`needs_rehash` 時以 ORM `update()` **條件式更新** `WHERE id = :id AND password_hash = :old`，影響 0 列即放棄、不覆寫（ADR-005 第 2 節、ADR-003 2.1 第 5 點）。
  - 安全日誌依 security-logging.md 第 2 節：`auth.login.success`、`auth.login.failure`（`reason` 五種；`username` 為正規化結果，格式不合法記 `username=null`、`username_invalid=true`）、`auth.login.locked`。
- [ ] **清理：單一入口 `AuthService.maybe_cleanup(now)`（本 Task 為呼叫點負責者，overview.md 3.1、ADR-001 第 5 節、ADR-005 第 5 節第 4 版）**：
  - 在 `authenticate` 中 **`reserve_attempt` 之後呼叫一次**（不論後續驗證成功或失敗、帳號是否存在）；**取代**第 3 版「成功路徑清 Session、reserve 路徑清 throttle、共用時間戳」的做法（該做法會使 Session 清理被餓死），成功路徑不再另外清理。
  - 距上次清理 ≥ T-007 的 `SESSION_CLEANUP_MIN_INTERVAL_SECONDS`（300）時，依序執行 `SessionStore.delete_expired`（T-007 提供）與 `LoginThrottleRepository.delete_stale`，各自另開 `immediate_transaction`；時間戳為模組層級，**先檢查、清理完成後才更新**。
  - 清理失敗（例如 `ServiceBusyError`）只記 `app` WARNING、不影響登入結果。**T-001 最終複審 NB-6**：失敗時**也更新時間戳**（避免鎖競爭時每次登入都重試清理、加重寫鎖競爭），下次清理延到下一個間隔；若實作選擇不更新，須在程式註解說明取捨並經 Code Reviewer 同意。多執行緒同時清理可接受（`DELETE` 冪等），不加 Lock。
- [ ] `app/routers/deps.py`：`get_current_user`（可為 None）、`require_login`（未登入拋 `LoginRequired(next_path, timed_out=request.state.session_expired)`）、`require_role(role)`（角色不符**只拋** `PermissionDeniedError(reason='role_required:<role>')`，**不寫日誌**；`access.denied` 由 T-023 的全域 handler 記錄，routes.md 第 1 節），以及 `get_auth_service` 等 service 工廠（overview.md 2.1）。
- [ ] 將 `current_user` 注入 Jinja2 context（routes.md 第 3 節）。
- [ ] `tests/fixtures/`：`cheap_password_service`（`argon2.profiles.CHEAPEST`）、`login_as(user)`。
- [ ] 測試（ADR-005 第 7 節）：
  - **`normalize_username` 表格測試**（ADR-005 2.1 表：`'ADMIN'`、`' admin '`、`'admin\n'`、KELVIN SIGN `'Kate'` → `'kate'`、`'İ'` → `None`、空字串 / 51 字 / `'a b'` / `'a@b'` → `None`）。
  - 雜湊與驗證、`needs_rehash`、密碼政策各條；未持有名額呼叫 `verify` → `RuntimeError`。
  - **needs_rehash 條件式更新**：先在另一個交易改掉 `password_hash`，再完成 rehash → 不覆寫較新的雜湊。
  - 四種失敗情境回傳相同結果；4 次失敗後第 5 次失敗觸發鎖定與 `auth.login.locked`；第 5 次密碼正確則成功並刪除列；鎖定中正確密碼仍失敗且 `attempt_count` 不增加、`locked_until` 不延長；`now + 900` 秒後可登入；時間窗過期重設；不存在帳號行為一致。
  - **併發**：同一帳號 20 個執行緒以 `threading.Barrier(20)` 同時以錯誤密碼呼叫 `authenticate`（各自 DB Session、同一暫存 SQLite 檔；名額設足夠大以免 503 干擾），spy 計數真實 `verify` 次數 **≤ 5**、全部回傳 `None`、最終 `attempt_count == 5` 且已鎖定；重複 10 輪。
  - **雜湊併發**：`PASSWORD_HASH_CONCURRENCY=2` 時同時進入雜湊數 ≤ 2；名額已滿時**立即（< 100 毫秒）**`ServiceBusyError`，且 `login_throttles` 沒有新增或變更。
  - **名額已滿彙總記錄**（ADR-005 第 7 節）：以可注入的時間來源（例如 `Clock` 或 monkeypatch）控制時間，依 NB-3 規則（取代 ADR-005 §7 原寫的「60 秒內 10 次只 1 筆、count=10」）：60 秒內連續 10 次被拒 → 只有 1 筆 `auth.login.busy` 且 `rejected_count=1`（第一次立即輸出）；第 61 秒再被拒 1 次 → 第 2 筆、`rejected_count=10`（先前累計 9 ＋ 本次 1）；之後計數重新起算；`caplog` 不含 username / 密碼。
  - **登入飽和時 `GET /venues` 仍可回應**（ADR-005 第 7 節）：`PASSWORD_HASH_CONCURRENCY=2`、monkeypatch `verify` 每次耗時 2 秒、20 個執行緒同時 `POST /login`；同時 `GET /venues` 在 1 秒內回 200；多餘的登入請求回 503。（需要 T-010 的 `/login` route 與 T-012 的 `/venues`；本 Task 可以測試專用的 sync route 模擬 `/login`、以任一公開 sync route 代替 `/venues`，T-021 再以實際 route 重跑，見技術備註。）
  - 清理（`maybe_cleanup`，以 `Clock` 推進時間驗證，ADR-005 第 7 節）：**連續多次成功登入且間隔超過 300 秒時，過期 Session 確實被刪除**（防止第 3 版「清理被餓死」退化）；只有失敗嘗試時，過期 Session 與 throttle 列也都會被清理；300 秒內不重複清理；清理拋 `ServiceBusyError` 時登入結果不受影響，且（依 NB-6）300 秒內不再重試、超過間隔後再清理。
  - 相依函式的允許與拒絕路徑；`require_role` 不符時拋例外且自身未呼叫 `security_log`。

## 技術備註
- 登入 / 登出的 web route 與頁面由 T-010 實作，本 Task 只提供 service 與相依函式。
- service 不處理 HTTP 細節；密碼以 `str` 參數傳入，不放進 Pydantic model（overview.md 第 5 節）。
- `normalize_username`、`PasswordService`、`LoginThrottleRepository.reset` 供 T-009（CLI 建帳號、`unlock-user`）使用，簽章依設計。
- 「登入飽和」測試的 route 依賴：`POST /login` 為 **sync route（`def`）**，才會與其他 sync route 共用 threadpool（ADR-005 第 6 節）；T-010 實作時必須維持 `def`。為避免本 Task 相依 T-010 / T-012（會拉長關鍵路徑），本 Task 以測試專用 route 驗證機制，T-021 以實際 `/login`、`/venues` 驗證。
- `access.denied` 的記錄依賴 T-023 的 handler（經 T-007 間接相依）。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（ASVS Level 2：認證 V6、存取控制 V8）
- [ ] QA 驗收通過
- [ ] 文件與 .env.example 已更新
