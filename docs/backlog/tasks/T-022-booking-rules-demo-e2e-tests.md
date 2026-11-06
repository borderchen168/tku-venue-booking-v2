---
id: T-022
title: 申請規則、併發與 Sprint Demo 端到端測試
story: [US-004, US-002, US-017, US-001]
status: todo        # todo / in-progress / review / done / blocked
assignee: tester
branch: feature/T-022-booking-rules-demo-e2e-tests
sprint: sprint-01
depends_on: [T-009, T-015, T-020]
created: 2026-11-06
---

# T-022 申請規則、併發與 Sprint Demo 端到端測試

## 說明
以 `TestClient` 驗證 Sprint 1 Demo 完整流程與 US-004 的所有拒絕情境（含併發），並整理 Demo 操作腳本供 Sprint Review 使用。

## 完成條件
- [ ] 端到端測試（Demo 流程）：訪客瀏覽場地清單 → 場地資訊 → 借用狀況 → 承辦人登入並新增考試週 → 學生登入並成功申請 → 借用狀況頁顯示該時段「審核中」且不含申請人個資。
- [ ] 拒絕情境（透過 HTTP，非直接呼叫 service）：時段重疊（AC5）、不開放日（AC10）、未達 5 個工作天（AC11）、未登入（AC2）、竄改 club_id（AC3）、staff 申請（AC4）、缺少 CSRF（AC16）、超出開放時間（AC8）。
- [ ] 併發：兩個不同學生的 HTTP 請求同時申請同一時段，只有一筆成功（AC7）。
- [ ] 承辦人新增不開放期間後，借用狀況頁立即標示、該期間申請立即被拒（EP-005 成功指標）。
- [ ] `docs/sprints/sprint-01/demo-script.md` 所需內容：Demo 資料建立步驟（引用 T-009 CLI）與操作步驟，交由 Scrum Master 寫入 sprint 文件（tester 不寫 `docs/sprints/`，以 Task 回報提供內容）。
- [ ] 發現的缺陷寫入 `docs/backlog/bugs/`。

## 技術備註
- 可寫入：`tests/`、`docs/backlog/bugs/`。
- 「今天」日期需可在測試中固定（依 T-019 / T-020 提供的注入方式），確保 R-13 測試不隨實際日期變動。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過
- [ ] QA 驗收通過（US-001、US-002、US-004、US-017 全部 AC）
- [ ] 文件與 .env.example 已更新
