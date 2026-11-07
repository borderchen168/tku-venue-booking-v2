---
id: T-002
title: 頁面流程、base layout 與 CSS 規範
story: [US-013, US-001, US-017, US-002, US-004]
status: done        # todo / in-progress / review / done / blocked
assignee: ui-ux-designer
branch: feature/T-002-ui-design-base-layout
sprint: sprint-01
depends_on: [T-001]
created: 2026-11-06
---

# T-002 頁面流程、base layout 與 CSS 規範

## 說明
依 T-001 的路由清單（`docs/architecture/routes.md`）設計 Sprint 1 的頁面流程與版面，建立所有頁面共用的 Jinja2 base layout、共用 macro(巨集)、全部錯誤頁與 CSS，
讓後續 Frontend Task 只需撰寫各頁內容區塊。所有樣板必須相容 overview.md 第 8 節的 CSP(內容安全政策)（不允許 inline、不允許 `data:`）。

## 完成條件
- [x] `docs/design/sprint-01-page-flow.md`：頁面流程（依 routes.md 第 6 節：訪客：場地清單 → 場地資訊 → 借用狀況；學生：登入 → 申請 → 結果；承辦人：登入 → 不開放期間管理）與各頁 wireframe(線框圖，文字或 ASCII 即可)。
- [x] `docs/design/style-guide.md`：色彩、字級、間距、按鈕、表單、狀態標籤（可申請／審核中／已核准／不開放（原因類型）／不開放（非學期期間））配色，符合 WCAG 2.1 AA 對比度；並寫入 routes.md 第 3、4 節的樣板變數與表單欄位名稱約定。
- [x] `app/templates/base.html`：`<html lang="zh-Hant-TW">`、標題區塊、依 `current_user` 角色顯示的導覽列（routes.md 2.1 `/` 說明：學生：申請場地；承辦人：不開放期間管理；Sprint 1 尚未實作的「我的申請」〔US-005〕、「待審核」〔US-006〕**隱藏**，不顯示「即將推出」或任何會導向 404 的連結，US-013 AC1）、登出按鈕（POST 表單，以 `forms.csrf_field()` 輸出 `csrf_token`）、flash 訊息區（`messages`）、主內容區塊。
- [x] `app/templates/macros/forms.html`：表單欄位、逐欄錯誤訊息（`errors` 字典，全域錯誤鍵 `__all__`）、`csrf_field()` macro；錯誤訊息以 `aria-describedby` 關聯欄位（routes.md 第 3 節）。
- [x] `app/templates/errors/`：`400.html`（表單解析失敗 / 欄位數超過上限，「請求格式不正確」）、`403.html`、`404.html`、`413.html`（chunked 本體過大，「送出的資料過大」）、`422.html`、`500.html`、`503.html`（「系統忙碌，請稍後再試」，含登入雜湊名額已滿）（routes.md 第 5 節、error-handling.md 第 3 節的訊息文字）；**每頁皆附「回首頁」連結**，可顯示 `request_id`（「錯誤代碼：…」），不顯示任何技術細節或使用者輸入值（error-handling.md 第 1 節原則 3）。
  - **不需要 `415.html`**：415 與 TrustedHost 400、`Content-Length` 400 / 413 屬路由前錯誤，由 middleware 回純文字（error-handling.md 3.2）。
  - `500.html` 與 `base.html` 必須在**沒有** `current_user` / `csrf_token` / `messages` 時也能渲染（500 可能發生在 Session 載入之前，context 值為 `None`，error-handling.md 3.2），導覽列顯示訪客版。
- [x] 所有 `<form>` 一律 `method="post"`（或 GET 查詢表單），**不得使用 `enctype="multipart/form-data"`**（非 urlencoded 的 POST 會被 415 擋下，routes.md 第 1 節、ADR-002 2.1）；style-guide 註明此規則。
- [x] `app/static/css/main.css`：不依賴外部 CDN；RWD(響應式設計) 支援手機寬度；圖示或背景不得使用 `data:` URI（CSP `img-src 'self'`）。
- [x] 樣板不得有 inline `<script>`、`<style>`、`style=` 屬性與任何 `on*=` 事件屬性（overview.md 第 8 節）；刪除確認等互動以獨立確認頁實作，不用 JS confirm。

## 技術備註
- 可寫入：`docs/design/`、`app/templates/`、`app/static/`。
- 樣板 context 變數（`current_user`、`csrf_token`、`messages`、`form`、`errors`、`app_timezone`）與 filter（`local_dt`、`status_label` 等）以 routes.md 第 3 節為唯一來源；列舉中文標籤一律用 filter，樣板不得自行寫死對照（overview.md 第 5 節）。
- 禁止 `|safe` 與 `Markup()` 輸出使用者輸入。
- 錯誤頁樣板未合併前，T-023 的 handler 會退回純文字 fallback（error-handling.md 3.3），兩者可平行開發。
- 可與 T-003 平行進行。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|
| 2026-11-07 | Security Reviewer | 通過（第 1 輪） | 無 blocking；實際渲染注入測試全數跳脫；建議 `next` 來源、`request_id` 由伺服器產生、`nav_link` 註解 → 已落實（routes.md 第 4 版、base.html） |
| 2026-11-07 | Code Reviewer | 需修正（第 1 輪） | B-1 週檢視整天 rowspan 會隱藏既有佔用（違反 US-002 AC8）；N-1～N-9（標籤寫死、form_errors 參數、空訊息、對比度數值、CSS 細節等）→ 全數修正 |
| 2026-11-07 | Code Reviewer | 通過（第 2 輪） | B-1、N-1～N-9 已修；nit：非學期範例日期 → 改用 2026-12-28 週（跨學期末） |
| 2026-11-07 | Code Reviewer | 通過（第 3 輪） | 渲染測試（191 個）涵蓋完成條件；non-blocking：CSP 掃描註解移除與屬性前綴、select 型別比對、輸出空白 → 已修 |
| 2026-11-07 | Security Reviewer | 通過（第 2 輪） | 無 blocking；CSP 掃描 14 種繞過寫法 → 掃描器重寫 |
| 2026-11-07 | QA | 通過 | 完成條件 1～8 全數通過；US-013 AC1、US-002 AC6～AC8、US-017 入口相關部分通過；uvicorn 實測靜態檔 200 |
| 2026-11-07 | Code Reviewer | 通過（最終） | 空白控制調整前後 116 組渲染比對差異 0；major：掃描器把 HTML 規則套到 Jinja 程式碼造成誤判 → 規則分 jinja / markup / url / css 四類 |
| 2026-11-07 | Security Reviewer | 通過（最終） | 12/14 繞過已可偵測，其餘 2 個為已知限制；N-A～N-D（autoescape 任意值、xmlattr、空標籤切字、URL / CSS escape）→ 已修 |
| 2026-11-07 | Orchestrator | 確認 | 最終修正僅涉及測試；ruff / format / mypy / pytest 548 passed、coverage 100%、pip_audit 無漏洞；抽查合法樣板無誤判、違規可偵測 |

## DoD(完成定義)
- [x] ruff check / ruff format --check / mypy 通過
- [x] pytest 通過，branch coverage ≥ 80%（base layout 渲染測試可於 T-003 合併後補上）
- [x] Code Review 通過
- [x] Security Review 通過（autoescape、CSP 相容）
- [x] QA 驗收通過
- [x] 文件與 .env.example 已更新
