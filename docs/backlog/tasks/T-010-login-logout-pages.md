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
實作登入頁、登入送出、登出與首頁的角色選單，串接 T-007 Session / CSRF 與 T-008 認證服務，完成 US-013 的使用者可見流程。

## 完成條件
- [ ] `GET /login`：登入表單（含 CSRF 隱藏欄位）；若帶逾時提示參數或 Session 狀態，顯示「登入已逾時，請重新登入」。
- [ ] `POST /login`：驗證 CSRF → 呼叫 `authenticate` → 成功時 `regenerate()` Session、導向首頁；失敗時一律顯示「帳號或密碼錯誤」（AC2、AC3、AC4、AC10），HTTP 狀態碼與頁面內容在各失敗情境一致。
- [ ] `POST /logout`：驗證 CSRF → `destroy()` → 導向首頁（AC5）。
- [ ] 首頁 `GET /`：顯示使用者名稱與依角色的選單（AC1）；未登入時顯示公開入口（場地清單）。
- [ ] 登入成功後的導向僅允許站內相對路徑（防 Open Redirect(開放式重新導向)，CWE-601）。
- [ ] 整合測試（`TestClient`）：AC1、AC2、AC5、AC6、AC7、AC8、AC10 的主要路徑與負面路徑。

## 技術備註
- 可寫入：`app/templates/`、`app/static/`、`app/routers/web/`、`tests/`。
- 若需要調整 service 介面，回報 Orchestrator 由 backend-developer 處理。
- 密碼欄位 `autocomplete="current-password"`，送出失敗時不回填密碼。

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
