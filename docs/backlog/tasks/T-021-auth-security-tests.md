---
id: T-021
title: 認證與 Session 安全負面測試
story: US-013
status: todo        # todo / in-progress / review / done / blocked
assignee: tester
branch: feature/T-021-auth-security-tests
sprint: sprint-01
depends_on: [T-009, T-010, T-012]
created: 2026-11-06
---

# T-021 認證與 Session 安全負面測試

## 說明
獨立於開發者，依 US-013 驗收條件、AGENTS.md 2.3 與設計文件（ADR-001、ADR-002、ADR-005、error-handling.md 第 5 節、security-logging.md 第 4 節、routes.md 第 1 節）
補足認證、Session、CSRF 的負面測試與邊界測試，發現問題時建立 Bug。

## 完成條件
- [ ] `tests/integration/test_auth_security.py`（或依現有結構）涵蓋：
  - AC2：五種失敗原因（不存在、密碼錯、停用、鎖定、格式不符）狀態碼皆 400、HTML 本體除 CSRF Token 值外逐字相同；回應時間以正式 argon2 參數多次取樣比較中位數（ADR-005 第 7 節；可依 planning.md 縮減順序第 4 項降為人工檢查）。
  - AC3：15 分鐘內失敗 5 次後第 6 次即使密碼正確也被拒；鎖定時間過後可登入（以 `FixedClock` 注入，不實際等待）；**同一帳號併發登入時真實密碼驗證次數 ≤ 5**（HTTP 層，ADR-005 第 7 節；雜湊名額不等待，超出 `PASSWORD_HASH_CONCURRENCY` 的請求回 503，斷言時每個回應須為 400 或 503，且 503 的請求不增加 `attempt_count`）。
  - **登入飽和不影響其他頁面**（ADR-005 第 7 節，以實際 route 重跑 T-008 的機制測試）：`PASSWORD_HASH_CONCURRENCY=2`、monkeypatch `verify` 每次耗時 2 秒、20 個執行緒同時 `POST /login`，同時 `GET /venues` 在 1 秒內回 200，多餘登入請求回 503。
  - **`unlock-user` 後可立即以正確密碼登入**（cli.md 3.4）。
  - AC4：停用帳號正確密碼仍失敗、不建立 Session。
  - AC5：登出後以舊 Cookie 存取需登入頁面被導向登入頁。
  - AC6：閒置逾時（含 `reason=timeout` 提示）；AC12：絕對逾時。AC7：Cookie 屬性（含 production `Secure` 與 `__Host-` 名稱）。
  - AC8：登入、登出缺少 / 錯誤 CSRF Token 回應 403；未先 `GET /login` 直接 POST → 403 且 `csrf.failed` 的 `reason=no_nonce`；未登入 POST /logout → 403 且 `reason=no_session`。
  - **登入前 Token 與 nonce**（ADR-002 4.2～4.5、第 5 節）：
    - 竄改 Token mac、竄改 / 替換 nonce Cookie、以另一瀏覽器的 nonce 搭配本 Token 皆 403（`mismatch`）；nonce 格式不合 → 403（`no_nonce`）。
    - **Token 過期**：以 `FixedClock` 推進超過 `LOGIN_CSRF_MAX_AGE_SECONDS` → 403 且 `reason=expired`；重新 `GET /login` 後可正常登入。
    - **nonce 每次刷新**：連續 `GET /login` 每次回應都有 nonce `Set-Cookie`（`Max-Age=LOGIN_CSRF_MAX_AGE_SECONDS`、`SameSite=Lax`），且值不變。
    - **多分頁加外站連入**：同一 Client 開啟兩個登入頁取得 Token A、B，再以跨站標頭（`Referer: https://example.org/`、`Sec-Fetch-Site: cross-site`）`GET /login` 取得 Token C；A、B、C 皆可成功登入（nonce 未被覆寫，ADR-002 第 5 節）。
    - **刪除 Cookie 帶 Secure**：`SESSION_COOKIE_SECURE=true`（`__Host-` 名稱）時，登入成功刪除 nonce Cookie、登出刪除 Session Cookie 的 `Set-Cookie` 皆含 `Max-Age=0`、`Path=/`、`HttpOnly`、`SameSite=Lax`、`Secure`（ADR-002 4.5）。
  - **所有 POST route 不帶 Token 皆 403**（routes.md 第 1 節、ADR-002 2.1 第 3 點；**T-001 最終複審 NB-4：測試檔由 T-023 建立、本 Task 驗收**）：以 T-023 的 `iter_api_routes(app, routers=ALL_ROUTERS)` 走訪 **`app.router.routes` ＋ `ALL_ROUTERS` 各 router 的 `.routes`**（**不可**只走訪 `app.routes`），對接受 POST 的 route（路徑參數代入 `1`）不帶 Token 送出，已登入與未登入各跑一次皆 403；**目前已掛載的**每個 `APIRoute` 都是 `LimitedFormRoute`；收集到的 POST 路徑包含當時的 `EXPECTED_POST_PATHS`（至少 `/login`、`/logout`）。
  - `EXPECTED_POST_PATHS` 與實際 POST 路徑「**等於** routes.md 的 6 條」的**最終驗收移到 T-022**（需等 T-015、T-020 合併；2026-11-06 Orchestrator 決定，planning.md）。本 Task 的測試以走訪方式撰寫，T-015 / T-020 合併後新增的 POST route 會自動納入 403 檢查。
  - **表單 Content-Type 與欄位數**（error-handling.md 3.1、ADR-002 2.1，以實際 route 驗證）：對 `POST /login`（帶 `Form()` 參數）送 `multipart/form-data`（含 / 不含檔案）與 `application/json` → **415 純文字**且帶安全標頭；送 51 個欄位（帶正確登入前 Token 與 nonce）→ **400**（`errors/400.html`），且不執行登入、`login_throttles` 不變。
  - AC9：CLI 弱密碼、常見密碼被拒、非 TTY 拒絕。AC10：帳號空白、51 字、非白名單字元、密碼空白或超過 128 字元，回應皆與 AC2 相同。
  - Session Fixation：登入前帶舊 Session Cookie，登入後 Session ID 不同且舊 Cookie 失效；nonce Cookie 值與 Session ID 無關。
  - AC11：**匿名瀏覽（`/`、`/venues`、`GET /login` 多次）與登入失敗後 `user_sessions` 筆數為 0**（ADR-001 第 7 節）。
  - 日誌：以 `caplog` 斷言全文不含密碼、Session Cookie 值、CSRF Token、nonce、`display_name`（security-logging.md 第 4 節）；**格式錯誤的登入（51 字帳號 + 密碼）回應本體與日誌不含密碼**；**500 路徑**（monkeypatch `AuthService.authenticate` 拋例外並送含密碼的表單）回 500、本體無 stack trace、日誌不含密碼與 CSRF Token（error-handling.md 第 5 節）。
- [ ] 發現的缺陷寫入 `docs/backlog/bugs/BUG-NNN-*.md`，附重現步驟。

## 技術備註
- 可寫入：`tests/`、`docs/backlog/bugs/`。
- 2026-11-06（T-001 第 4 版）：`EXPECTED_POST_PATHS` 最終清單驗收需要 T-015、T-020，為維持本 Task 在波次 7，該項移給 T-022；本 Task 不相依 T-015、T-020。
- 新增相依 T-012：「登入飽和」測試需要實際的 `GET /venues`（T-012 於波次 5 合併，早於本 Task 的波次 7，不影響排程）。
- 每個測試使用獨立暫存 SQLite；一般測試可用 `cheap_password_service`，回應時間比較需使用正式參數。
- 「所有 POST route 不帶 Token 皆 403」測試會自動涵蓋日後新增的 POST route，請放在不易被刪除的位置並在測試 docstring 說明用途。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過
- [ ] QA 驗收通過
- [ ] 文件與 .env.example 已更新
