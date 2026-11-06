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
實作密碼雜湊、帳號驗證、登入失敗鎖定與安全日誌，以及 route 共用的身分與角色檢查相依函式（預設拒絕）。

## 完成條件
- [ ] `app/core/security.py`（或 `app/services/password.py`）：argon2（`argon2-cffi`）雜湊與驗證、需要時 rehash；密碼政策：長度 8～128、檢查常見密碼清單（清單檔以 UTF-8 存放於 repo，`pathlib.Path` 讀取）。
- [ ] `app/repositories/user_repository.py`、`app/services/auth_service.py`：
  - `authenticate(username, password)`：帳號不存在、密碼錯誤、帳號停用、鎖定中皆回傳相同的失敗結果（US-013 AC2、AC3、AC4）；帳號不存在時仍執行一次假雜湊驗證以降低時間差。
  - 登入失敗鎖定：同一帳號 `LOGIN_LOCKOUT_SECONDS` 內失敗 `LOGIN_MAX_ATTEMPTS` 次後鎖定 `LOGIN_LOCKOUT_SECONDS`；成功登入後重設計數。
  - 帳號輸入驗證：1～50 字、僅英數字與 `._-`（Pydantic schema，US-013 AC10）。
- [ ] 安全日誌：登入成功、登入失敗、鎖定、權限拒絕（只記錄帳號識別或 user id、來源 IP、事件類型，不記錄密碼）。
- [ ] 相依函式：`get_current_user`（可為 None）、`require_login`（未登入 → 導向登入頁；逾時 → 導向登入頁並帶逾時提示）、`require_role(role)`（角色不符 → 403 並記錄權限拒絕日誌）。
- [ ] 將 `current_user` 注入 Jinja2 context（供 T-002 導覽列使用）。
- [ ] 單元測試：雜湊與驗證、密碼政策、四種失敗情境回傳相同結果、鎖定門檻與解除、相依函式的允許與拒絕路徑。

## 技術備註
- 登入 / 登出的 web route 與頁面由 T-010 實作，本 Task 只提供 service 與相依函式。
- service 不處理 HTTP 細節；`require_*` 相依函式屬 router 層共用工具，可放在 `app/routers/deps.py`。

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
