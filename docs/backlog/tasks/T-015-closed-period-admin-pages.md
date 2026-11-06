---
id: T-015
title: 不開放期間管理頁
story: US-017
status: todo        # todo / in-progress / review / done / blocked
assignee: frontend-developer
branch: feature/T-015-closed-period-admin-pages
sprint: sprint-01
depends_on: [T-002, T-010, T-013]
created: 2026-11-06
---

# T-015 不開放期間管理頁

## 說明
實作承辦人專用的不開放日期 / 期間管理頁（列表、新增、編輯、刪除），完成 US-017。

## 完成條件
- [ ] 列表頁：依起日排序顯示期間、類型、說明，提供編輯與刪除。
- [ ] 新增 / 編輯表單：起日、迄日、類型（下拉白名單）、說明；驗證失敗時逐欄顯示錯誤並保留已填資料（AC5）。
- [ ] 新增成功後顯示受影響的既有申請清單（AC3；取消連結待 US-012）。
- [ ] 刪除以 POST 表單送出並需確認，不使用 GET 改變狀態。
- [ ] 所有路由套用 `require_role('staff')`：學生 403、未登入導向登入頁（AC6）；所有 POST 驗證 CSRF（AC7）。
- [ ] 整合測試：AC1、AC3、AC4、AC5、AC6、AC7（含學生 403、未登入導向、缺少 CSRF 403 且資料不變）。

## 技術備註
- 可寫入：`app/templates/`、`app/static/`、`app/routers/web/`、`tests/`。
- 路徑依 T-001 routes.md（建議 `/admin/closed-periods`）。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（存取控制、CSRF）
- [ ] QA 驗收通過（US-017）
- [ ] 文件與 .env.example 已更新
