---
id: T-002
title: 頁面流程、base layout 與 CSS 規範
story: [US-013, US-001, US-017, US-002, US-004]
status: todo        # todo / in-progress / review / done / blocked
assignee: ui-ux-designer
branch: feature/T-002-ui-design-base-layout
sprint: sprint-01
depends_on: [T-001]
created: 2026-11-06
---

# T-002 頁面流程、base layout 與 CSS 規範

## 說明
依 T-001 的路由清單設計 Sprint 1 的頁面流程與版面，建立所有頁面共用的 Jinja2 base layout、共用 macro(巨集) 與 CSS，
讓後續 Frontend Task 只需撰寫各頁內容區塊。

## 完成條件
- [ ] `docs/design/sprint-01-page-flow.md`：頁面流程（訪客：場地清單 → 場地資訊 → 借用狀況；學生：登入 → 申請 → 結果；承辦人：登入 → 不開放期間管理）與各頁 wireframe(線框圖，文字或 ASCII 即可)。
- [ ] `docs/design/style-guide.md`：色彩、字級、間距、按鈕、表單、狀態標籤（可申請／審核中／已核准／不開放）配色，符合 WCAG 2.1 AA 對比度。
- [ ] `app/templates/base.html`：`<html lang="zh-Hant-TW">`、標題區塊、依登入狀態與角色顯示的導覽列（學生：我的申請、申請場地；承辦人：待審核、管理功能；Sprint 1 尚未實作的項目可先隱藏或標示）、登出按鈕（POST 表單，預留 `csrf_token` 欄位）、flash 訊息區、主內容區塊。
- [ ] `app/templates/macros/forms.html`：表單欄位、逐欄錯誤訊息、隱藏 CSRF 欄位的 macro；錯誤訊息以 `aria-describedby` 關聯欄位。
- [ ] `app/templates/errors/`：403、404、422、500 錯誤頁（不顯示任何技術細節）。
- [ ] `app/static/css/main.css`：不依賴外部 CDN（配合 CSP `default-src 'self'`）；RWD(響應式設計) 支援手機寬度。
- [ ] 不使用 inline script 與 inline style（配合 CSP）。

## 技術備註
- 可寫入：`docs/design/`、`app/templates/`、`app/static/`。
- 樣板變數名稱（如 `current_user`、`csrf_token`、`messages`）需與 T-003、T-007 約定一致，請以 T-001 的 routes.md 為準並寫入 style-guide。
- 禁止 `|safe` 與 `Markup()` 輸出使用者輸入。
- 可與 T-003 平行進行。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%（base layout 渲染測試可於 T-003 合併後補上）
- [ ] Code Review 通過
- [ ] Security Review 通過（autoescape、CSP 相容）
- [ ] QA 驗收通過
- [ ] 文件與 .env.example 已更新
