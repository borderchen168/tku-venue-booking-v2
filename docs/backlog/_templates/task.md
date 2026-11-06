---
id: T-000
title: <Task 名稱>
story: US-000
status: todo        # todo / in-progress / review / done / blocked
assignee:           # 負責的 subagent，例如 backend-developer
branch: feature/T-000-<slug>
sprint:
depends_on: []
created: YYYY-MM-DD
---

# T-000 <Task 名稱>

## 說明
<要完成的工作內容>

## 完成條件
- [ ]

## 技術備註
-

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（如適用）
- [ ] QA 驗收通過
- [ ] 文件與 .env.example 已更新
