---
id: T-007
title: Server-side Session 與 CSRF 機制
story: US-013
status: todo        # todo / in-progress / review / done / blocked
assignee: backend-developer
branch: feature/T-007-session-csrf
sprint: sprint-01
depends_on: [T-003, T-005]
created: 2026-11-06
---

# T-007 Server-side Session 與 CSRF 機制

## 說明
依 ADR-001、ADR-002 實作伺服器端 Session 與 CSRF Token 驗證，作為登入（US-013）與所有會改變狀態之表單（US-017、US-004）的共用安全機制。

## 完成條件
- [ ] Session 管理（`app/core/security.py` 或 `app/core/session.py`）：以 `secrets` 產生高強度 Session ID；Session 資料存於伺服器端（T-005 的資料表），Cookie 只放 Session ID（或其簽章值）。
- [ ] Cookie 屬性：`HttpOnly`、`SameSite=Lax`、`Path=/`；`SESSION_COOKIE_SECURE`（production 必為 true）控制 `Secure`；名稱來自 `SESSION_COOKIE_NAME`。
- [ ] 提供 `regenerate()`（登入後重新產生 Session ID，舊 ID 失效，防 CWE-384）、`destroy()`（登出時刪除伺服器端資料並清除 Cookie）。
- [ ] 閒置逾時：超過 `SESSION_MAX_AGE_SECONDS` 未活動即失效，並讓後續請求能辨識「逾時」以顯示提示（US-013 AC6）；每次請求更新最後活動時間。
- [ ] CSRF：每個 Session（含未登入的匿名 Session，供登入表單使用）綁定 CSRF Token；所有 POST/PUT/PATCH/DELETE 請求驗證表單欄位或標頭中的 Token，以常數時間比較；缺少或錯誤回應 403；Token 注入 Jinja2 context。
- [ ] 過期 Session 的清理機制（例如登入時或定期清理），避免資料表無限成長。
- [ ] 測試（含負面測試）：Cookie 屬性、production 有 `Secure`、regenerate 後舊 ID 失效、destroy 後舊 Cookie 無效、閒置逾時、缺少 / 錯誤 CSRF Token 回應 403、正確 Token 通過。

## 技術備註
- 不使用 Starlette `SessionMiddleware`（簽章 Cookie 無法於伺服器端銷毀），除非 ADR-001 另有決定。
- 日誌禁止記錄 Session ID、CSRF Token。
- 若新增設定（例如清理間隔），同步更新 `.env.example`。

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
