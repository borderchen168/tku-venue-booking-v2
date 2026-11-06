---
id: T-017
title: 借用狀況週檢視頁
story: US-002
status: todo        # todo / in-progress / review / done / blocked
assignee: frontend-developer
branch: feature/T-017-availability-page
sprint: sprint-01
depends_on: [T-002, T-012, T-016]
created: 2026-11-06
---

# T-017 借用狀況週檢視頁

## 說明
實作公開（不需登入）的單一場地週借用狀況頁，完成 US-002。

## 完成條件
- [ ] 週檢視表格：列 08:00–22:00（30 分鐘一格）、欄為週一至週日；狀態標籤「已核准」、「審核中」、「可申請」、「不開放（原因類型）」，配色依 T-002 style-guide，且不只以顏色區分（附文字，無障礙）。
- [ ] 上一週 / 下一週 / 選擇日期的導覽（GET 查詢參數，如 `week_start`）。
- [ ] 不合法或超出範圍的日期：回應 422 或導回本週，並顯示易懂訊息（AC6）。
- [ ] 活動名稱、社團名稱經 autoescape 輸出（CWE-79）。
- [ ] 場地資訊頁（T-012）的連結可正確進入本頁。
- [ ] 整合測試：AC1～AC6，含頁面原始碼不含申請人姓名、帳號、活動說明（AC2），XSS 字串被跳脫。

## 技術備註
- 可寫入：`app/templates/`、`app/static/`、`app/routers/web/`、`tests/`。
- 不使用 inline script；若需互動，JS 放 `app/static/js/`。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（XSS、個資）
- [ ] QA 驗收通過（US-002）
- [ ] 文件與 .env.example 已更新
