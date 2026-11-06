---
id: T-001
title: 系統架構、ERD、API 與路由設計
story: [US-013, US-001, US-017, US-002, US-004]
status: done        # todo / in-progress / review / done / blocked
assignee: system-analyst
branch: feature/T-001-architecture-design
sprint: sprint-01
depends_on: []
created: 2026-11-06
---

# T-001 系統架構、ERD、API 與路由設計

## 說明
Sprint 1 所有開發 Task 的設計基礎。依 AGENTS.md 1.4 分層原則與 Sprint 1 選入的 Story（US-013、US-001、US-017、US-002、US-004），
產出系統架構、資料模型 ERD(實體關聯圖)、web route 與表單清單，以及關鍵設計決策的 ADR(架構決策紀錄)，供 DBA、Backend、Frontend、UI/UX 依循。

## 使用者決定的設計輸入（2026-11-06）
1. **工作天**：本階段只算週一～週五，不考慮國定假日與補班；R-13 計算不依賴不開放期間資料。
2. **固定借用**：每次使用仍需社團送出申請。固定保留時段（fixed reservation，US-009）雖不在 Sprint 1，ERD 需預留不必大改的模型：
   例如 `fixed_reservations`（場地、社團、學期、星期幾、起訖時間、狀態），社團依保留時段送出的每次申請仍為一筆 `booking_applications`（可選填關聯欄位指向保留時段）。
   ADR-003 需說明未來重疊檢查如何把固定保留時段納入佔用判斷（Sprint 1 不實作）。
3. **不補件**：無「退回補件」狀態，退回即駁回，由學生重新申請。
4. **學期區間**：暫定每年 9/1～12/31（上學期）、3/1～6/30（下學期）。請在 ADR 或 erd.md 說明設定方式
   （例如以單一來源常數 / `.env` 設定月日區間，或 `semesters` 資料表），並說明如何依日期判斷所屬學期，供 US-009 固定保留時段與 US-018 寒暑假時段使用。
   **Sprint 1 即需實作「依日期判斷是否在學期區間內」**：US-004 AC17 規定學期以外的日期一律拒絕（T-019 使用）；固定保留時段與寒暑假時段仍只需設計。

## 完成條件
- [ ] `docs/architecture/overview.md`：分層架構（routers → services → repositories → models）、模組清單與各 Task 對應的檔案位置。
- [ ] `docs/architecture/erd.md`：Sprint 1 資料表與欄位（型別、nullable、唯一、外鍵、索引、CHECK），至少涵蓋：
  `users`（含 role、is_active）、`clubs`、社團負責人關聯、`venues`（含 category、capacity、is_active）、
  `closed_periods`（起迄日、類型列舉、說明）、`booking_applications`（場地、社團、申請人、起訖 UTC 時間、狀態列舉、活動名稱/說明/人數）、
  Session 與登入失敗紀錄所需的資料表。申請狀態列舉為 `pending`（審核中）、`approved`（已核准）、`rejected`（已駁回）、`cancelled`（已取消），**不含**「退回補件」（使用者決定：不補件，直接退回重新申請）。
- [ ] `docs/architecture/routes.md`：web route 清單（method、path、角色權限、CSRF、對應 Story/AC、成功與錯誤回應），包含公開頁、登入/登出、不開放期間管理、申請表單。
- [ ] 管理指令（CLI）介面規格：`create-staff`、`create-club`、`create-student`（含指定社團負責人）的參數與驗證規則。
- [ ] ADR（`docs/architecture/adr/ADR-NNN-*.md`），至少：
  - ADR-001 Server-side Session(伺服器端會話) 儲存方式（需支援登出銷毀、重新產生 Session ID、閒置逾時；說明為何不用 Starlette 簽章 Cookie Session）。
  - ADR-002 CSRF Token 機制（Synchronizer Token 綁定 Session；登入頁未登入時的處理方式）。
  - ADR-003 預約時段重疊檢查（`BEGIN IMMEDIATE` 交易、半開區間 `[start, end)`、佔用狀態集合、併發測試策略）。
  - ADR-004 時間與時區處理（UTC 儲存、Asia/Taipei 判斷日期與工作天（R-13 工作天＝週一～週五，不考慮國定假日與補班）、SQLite 存放 timezone-aware datetime 的方式）。
  - ADR-005 登入失敗鎖定（以帳號計數、時間窗、與帳號不存在時的處理以避免帳號列舉）。
  - ADR-006 學期區間與固定保留時段的資料模型預留（見上方設計輸入 2、4）。
- [ ] 錯誤處理規格：404/403/422/500 的呈現方式（統一錯誤頁、不洩漏 stack trace）。
- [ ] 安全日誌事件清單與欄位（登入成功/失敗/鎖定、權限拒絕、不開放期間異動、申請建立），註明禁止記錄的欄位。

## 技術備註
- 只寫入 `docs/architecture/`。
- 本 Task 完成並合併後，T-002、T-003 才開始；ERD 若後續需調整，以新的 ADR 或修訂紀錄說明。
- Sprint 1 不提供 JSON API（`routers/api/`），全部為 Jinja2 SSR 表單；若 SA 判斷需要，請於 routes.md 說明。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|
| 2026-11-06 | code-reviewer | 需修改 → 通過 | 共 4 輪；第 1～3 輪 blocking：WAL 寫入交易、BUSY extended code、模組負責 Task、表單限制無效、route 走訪測試；第 4 版通過，剩餘 non-blocking 已寫入 T-008、T-019、T-020、T-023 |
| 2026-11-06 | security-reviewer | 需修改 → 通過 | 第 1 輪 blocking：登入鎖定 TOCTOU；第 2、3 輪通過，non-blocking 已於第 3、4 版處理 |

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過（不適用：純文件）
- [ ] pytest 通過，branch coverage ≥ 80%（不適用：純文件）
- [x] Code Review 通過（設計審查）
- [x] Security Review 通過（Session、CSRF、鎖定、個資欄位設計）
- [ ] QA 驗收通過（設計涵蓋所有選入 Story 的 AC）——未另行執行：依使用者指示於 Code Review 通過後合併；設計對 AC 的涵蓋由 Code Reviewer 第 1 輪確認，Story 驗收時由 QA 一併檢查
- [x] 文件已更新（.env.example 新增設定由 T-003 負責）
