---
id: T-021
title: 認證與 Session 安全負面測試
story: US-013
status: todo        # todo / in-progress / review / done / blocked
assignee: tester
branch: feature/T-021-auth-security-tests
sprint: sprint-01
depends_on: [T-009, T-010]
created: 2026-11-06
---

# T-021 認證與 Session 安全負面測試

## 說明
獨立於開發者，依 US-013 驗收條件與 AGENTS.md 2.3 補足認證、Session、CSRF 的負面測試與邊界測試，發現問題時建立 Bug。

## 完成條件
- [ ] `tests/integration/test_auth_security.py`（或依現有結構）涵蓋：
  - AC2：帳號不存在與密碼錯誤的回應狀態碼、頁面內容一致；回應時間差異在合理範圍（以多次取樣比較，避免 flaky）。
  - AC3：15 分鐘內失敗 5 次後第 6 次即使密碼正確也被拒；鎖定時間過後可登入（以時間注入或 monkeypatch，不實際等待）。
  - AC4：停用帳號正確密碼仍失敗、不建立 Session。
  - AC5：登出後以舊 Cookie 存取需登入頁面被導向登入頁。
  - AC6：閒置逾時。AC7：Cookie 屬性（含 production `Secure`）。AC8：登入、登出缺少 / 錯誤 CSRF Token 回應 403。
  - AC9：CLI 弱密碼、常見密碼被拒。AC10：帳號空白、51 字、非白名單字元。
  - Session Fixation：登入前後 Session ID 不同。
  - 日誌不含密碼、Session ID、CSRF Token（以 `caplog` 檢查）。
- [ ] 發現的缺陷寫入 `docs/backlog/bugs/BUG-NNN-*.md`，附重現步驟。

## 技術備註
- 可寫入：`tests/`、`docs/backlog/bugs/`。
- 每個測試使用獨立暫存 SQLite。

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
