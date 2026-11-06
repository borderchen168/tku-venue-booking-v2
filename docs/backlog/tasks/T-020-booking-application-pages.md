---
id: T-020
title: 借用申請表單與送出結果頁
story: US-004
status: todo        # todo / in-progress / review / done / blocked
assignee: frontend-developer
branch: feature/T-020-booking-application-pages
sprint: sprint-01
depends_on: [T-010, T-017, T-019]
created: 2026-11-06
---

# T-020 借用申請表單與送出結果頁

## 說明
實作學生申請臨時借用的表單頁、送出處理與結果頁，完成 US-004 的使用者可見流程。

## 完成條件
- [ ] `GET` 申請頁：套用 `require_role('student')`；未登入導向登入頁（AC2）；社團下拉只列出該學生負責的社團；場地下拉只列出啟用中場地；可由借用狀況頁帶入場地與日期。
- [ ] `POST` 送出：驗證 CSRF（AC16）→ 呼叫 `booking_service.apply`；成功導向結果頁顯示申請編號與「已送出，待課外組承辦人審核」，並明示「未核准前不得使用場地（R-16）」（AC1）。
- [ ] 失敗處理：權限錯誤 403（AC3、AC4）；場地不存在 / 停用 404 或 422（AC14）；其他規則錯誤（AC5、AC8～AC13、AC15）在表單逐欄或頂部顯示訊息並保留已填資料。
- [ ] 時間欄位以 30 分鐘為間隔的選單，限制 08:00–22:00（伺服器端仍需驗證）。
- [ ] 借用狀況頁（T-017）在學生登入時提供「申請此場地」入口。
- [ ] 整合測試：AC1（送出後借用狀況頁顯示審核中）、AC2、AC3、AC4、AC16 與至少一個規則錯誤的顯示與資料保留。

## 技術備註
- 可寫入：`app/templates/`、`app/static/`、`app/routers/web/`、`tests/`。
- router 不直接操作 Session；`today` 由 router 以 Asia/Taipei 取得後傳入 service（或由 service 內部取得，依 T-019 介面）。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（CSRF、存取控制）
- [ ] QA 驗收通過（US-004）
- [ ] 文件與 .env.example 已更新
