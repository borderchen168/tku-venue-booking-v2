---
id: T-009
title: 管理指令 CLI（建立承辦人、社團、學生）
story: [US-013, US-004]
status: todo        # todo / in-progress / review / done / blocked
assignee: backend-developer
branch: feature/T-009-admin-cli
sprint: sprint-01
depends_on: [T-008]
created: 2026-11-06
---

# T-009 管理指令 CLI（建立承辦人、社團、學生）

## 說明
提供管理指令建立第一個承辦人帳號（US-013 AC9），以及 Sprint 1 Demo 所需的社團與學生（社團負責人）資料（US-014 維護介面尚未實作）。

## 完成條件
- [ ] `python -m app.cli create-staff`：互動輸入帳號、姓名、密碼（以 `getpass` 隱藏輸入、需輸入兩次確認）；套用 T-008 的密碼政策，少於 8 字元或常見密碼時拒絕；密碼以 argon2 雜湊儲存。
- [ ] `python -m app.cli create-club`：建立社團（名稱唯一、長度驗證）。
- [ ] `python -m app.cli create-student`：建立學生帳號並指定負責的社團（可多個）。
- [ ] 帳號格式與 T-008 相同的白名單驗證；帳號重複時回報錯誤且不建立。
- [ ] CLI 只呼叫 service / repository，不寫入原始 SQL；結束碼：成功 0、失敗非 0；錯誤訊息不輸出 stack trace 或密碼。
- [ ] 使用標準函式庫 `argparse`（或已在相依清單中的套件），跨平台可執行。
- [ ] 各指令提供 `--help` 說明；完成回報中附上 Demo 資料建立步驟（承辦人、2 個社團、2 位學生負責人），由 Scrum Master 寫入 `docs/sprints/sprint-01/demo-script.md`。
- [ ] 測試：三個指令的成功與失敗路徑（以 monkeypatch 模擬輸入）、弱密碼被拒、重複帳號被拒。

## 技術備註
- 不提供以命令列參數傳入明碼密碼的方式（避免留在 shell history）。
- 建立帳號時記錄安全日誌（不含密碼）。

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
