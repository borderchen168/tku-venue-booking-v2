# Sprint 01 Planning(衝刺規劃)

- 期間：2026-11-09 ~ 2026-11-20（兩週，10 個工作天）
- Sprint Goal(衝刺目標)：**建立可執行、符合資安規範的系統基礎，並完成第一條端到端流程——訪客可查看場地與借用狀況、承辦人可設定不開放期間、學生登入後能以社團名義送出符合規定的借用申請，且不合規的申請一律被拒絕。**

## 範圍評估

### 結論：採用 PO 建議的 5 個 Story（25 點），不刪減 Story，但預先約定縮減順序

| 項目 | 評估 |
|---|---|
| 功能 Story | 25 點（US-013、US-001、US-017、US-002、US-004） |
| 基礎建設 | repo 只有骨架，需額外完成架構設計、app 骨架與設定、DB 連線與交易工具、Alembic 與資料模型、base layout、Session / CSRF 等 8 個 Task（T-001～T-008），工作量約相當於 8～10 點 |
| 合計 | 約 33～35 點等價工作量；第一個 Sprint 沒有歷史 Velocity(速度) 可參考 |

**保留全部 5 個 Story 的理由**：Sprint Goal 的 Demo 流程（訪客查詢 → 承辦人設定考試週 → 學生申請 → 規則拒絕 → 借用狀況顯示審核中）每一步都對應其中一個 Story，少任何一個都無法展示完整的增量：
- 拿掉 US-002 → 無法展示「申請後借用狀況頁顯示審核中」。
- 拿掉 US-017 → 無法展示「承辦人設定考試週、不開放日被拒」（R-03～R-05）。
- 拿掉 US-013 → 無法辨識學生身分與社團，US-004 的授權與 CSRF 無從驗證。

基礎建設 Task 本身也是所有後續 Sprint 的前提，延後只會把風險往後推。

### 預先約定的縮減順序（若第 6 個工作天結束時 T-013、T-018 尚未合併，依序啟用；調整 Story 範圍需 PO 同意）

1. **US-017 AC3（列出受影響的既有借用）** 移到與 US-012（承辦人取消）同一個 Sprint——其「取消連結」本來就依賴 US-012。
2. **US-017 AC4 的「編輯」** 延後（保留新增與刪除；需修改時先刪除再新增）。
3. **US-002 的週切換導覽** 簡化為只支援 `week_start` 查詢參數與「本週」，不做日期選擇器。
4. **T-021 的回應時間差異測試** 降為人工檢查並開 Issue 追蹤（鎖定、CSRF、Session 等其他負面測試不得縮減）。

以上縮減都不影響 Demo 主流程與任何資安強制項目。

## 選入的 Story

| Story | 標題 | Story Point | 優先順序 |
|---|---|---|---|
| US-013 | 使用者登入與登出 | 5 | 1（must，所有身分相關功能的前提） |
| US-001 | 公開瀏覽場地清單與場地資訊 | 2 | 2（must） |
| US-017 | 承辦人維護不開放日期與期間 | 5 | 3（must，US-002 AC4 與 US-004 AC10 不開放日期的資料來源） |
| US-002 | 公開查看場地借用狀況 | 5 | 4（must） |
| US-004 | 學生線上申請臨時借用活動場地 | 8 | 5（must） |
| **合計** | | **25** | |

> 學生帳號與社團資料於本 Sprint 以管理指令（T-009）建立，維護介面於 US-014 提供。

### 使用者已決定的業務規則（2026-11-06）

| # | 決定 | 影響的 Task |
|---|---|---|
| 1 | 工作日只算週一～週五，不考慮國定假日與補班 | T-014（不再需要假日資料）、T-013（移除供 R-13 的國定假日查詢）、T-019 |
| 2 | 固定借用每次仍需社團送申請 | T-001（ERD 預留 fixed reservation 模型，US-009 非本 Sprint）、T-018（註記未來佔用判斷納入固定保留時段） |
| 3 | 不退回補件，直接退回重新申請 | T-001、T-005、T-013、T-016、T-018：申請狀態僅 審核中／已核准／已駁回／已取消 |
| 4 | 學期暫定每年 9/1～12/31、3/1～6/30 | T-001（ADR-006 學期區間設定方式，本 Sprint 只設計不實作） |

## Task 拆解與分派

| Task | 標題 | Story | 負責角色 | 相依 | 可平行 |
|---|---|---|---|---|---|
| T-001 | 系統架構、ERD、API 與路由設計 | 全部 | system-analyst | — | 否（第一個） |
| T-002 | 頁面流程、base layout 與 CSS 規範 | 全部 | ui-ux-designer | T-001 | 與 T-003 平行 |
| T-003 | 專案骨架：FastAPI app、設定、日誌、錯誤處理與安全標頭 | 全部 | backend-developer | T-001 | 與 T-002 平行 |
| T-004 | DB 連線、PRAGMA 與交易工具 | 全部 | backend-developer | T-003 | 與 T-002、T-014 平行 |
| T-005 | Alembic 初始化與 Sprint 1 資料模型 migration | 全部 | dba | T-001, T-004 | 與 T-002、T-014 平行 |
| T-006 | 場地初始資料 data migration | US-001 | dba | T-005 | 與 T-007、T-011、T-018 平行 |
| T-007 | Server-side Session 與 CSRF 機制 | US-013 | backend-developer | T-003, T-005 | 與 T-006、T-011、T-018 平行 |
| T-008 | 認證服務與存取控制相依 | US-013 | backend-developer | T-005, T-007 | 與 T-012 平行 |
| T-009 | 管理指令 CLI（建立承辦人、社團、學生） | US-013, US-004 | backend-developer | T-008 | 與 T-010、T-013 平行 |
| T-010 | 登入／登出頁面與 web route | US-013 | frontend-developer | T-002, T-008 | 與 T-009、T-013 平行 |
| T-011 | 場地查詢 service | US-001 | backend-developer | T-005 | 與 T-006、T-007、T-018 平行 |
| T-012 | 場地清單與場地資訊頁 | US-001 | frontend-developer | T-002, T-006, T-011 | 與 T-008 平行 |
| T-013 | 不開放期間 service | US-017 | backend-developer | T-005, T-008 | 與 T-009、T-010 平行 |
| T-014 | R-13 工作天與最晚申請日計算（純函式，只算週一～週五） | US-004 | backend-developer | T-003 | 可提早做，與 T-004～T-013 平行 |
| T-015 | 不開放期間管理頁 | US-017 | frontend-developer | T-002, T-010, T-013 | 與 T-016、T-019、T-021 平行 |
| T-016 | 借用狀況週檢視查詢 service | US-002 | backend-developer | T-011, T-013 | 與 T-015、T-019、T-021 平行 |
| T-017 | 借用狀況週檢視頁 | US-002 | frontend-developer | T-002, T-012, T-016 | 與 T-019 平行 |
| T-018 | 時段重疊檢查與 BEGIN IMMEDIATE 寫入 | US-004 | backend-developer | T-004, T-005 | 與 T-006、T-007、T-011 平行 |
| T-019 | 借用申請 service（規則驗證、授權、日誌） | US-004 | backend-developer | T-008, T-011, T-013, T-014, T-018 | 與 T-015、T-016、T-017 平行 |
| T-020 | 借用申請表單與送出結果頁 | US-004 | frontend-developer | T-010, T-017, T-019 | 否 |
| T-021 | 認證與 Session 安全負面測試 | US-013 | tester | T-009, T-010 | 與 T-015～T-020 平行 |
| T-022 | 申請規則、併發與 Sprint Demo 端到端測試 | US-004, US-002, US-017, US-001 | tester | T-009, T-015, T-020 | 否（最後） |

Task 檔案：`docs/backlog/tasks/T-001-*.md` ～ `T-022-*.md`。

## 建議執行順序（波次）

同一波次內的 Task 可平行，各自在獨立 worktree 進行；前一波次的相依 Task 須**已 squash merge 回 `main`** 才開始下一個。

| 波次 | Task | 說明 |
|---|---|---|
| 0 | T-001 | SA 設計先行（ERD、routes、ADR），其餘全部依此 |
| 1 | T-002 ∥ T-003 | UI 規範 / base layout 與 app 骨架平行 |
| 2 | T-004 ∥ T-014 | DB 連線；工作天純函式可提早完成 |
| 3 | T-005 | 資料模型與初始 migration（關鍵路徑） |
| 4 | T-006 ∥ T-007 ∥ T-011 ∥ T-018 | 場地資料、Session/CSRF、場地 service、重疊交易 |
| 5 | T-008 ∥ T-012 | 認證服務；場地公開頁（**US-001 可在此波次先完成驗收**） |
| 6 | T-009 ∥ T-010 ∥ T-013 | CLI、登入頁（**US-013 功能完成**）、不開放期間 service |
| 7 | T-015 ∥ T-016 ∥ T-019 ∥ T-021 | 管理頁（**US-017 完成**）、借用狀況 service、申請 service、認證安全測試 |
| 8 | T-017 | 借用狀況頁（**US-002 完成**） |
| 9 | T-020 | 申請頁（**US-004 功能完成**） |
| 10 | T-022 | 端到端與 Demo 驗收測試，之後 QA 對全部 Story 驗收 |

**關鍵路徑(Critical Path)**：T-001 → T-003 → T-004 → T-005 → T-007 → T-008 → T-013 → T-016 → T-017 → T-020 → T-022（11 個 Task 串行）。
關鍵路徑上的 Task 應優先分派並優先審查；非關鍵路徑（T-002、T-006、T-011、T-012、T-014、T-018、T-021）用來填滿平行空檔。

### 分派原則

- **DBA 是唯一撰寫 migration 的角色**（T-005、T-006 串行），其他 Task 若需要 schema 變更，回報 Orchestrator 改派 DBA，避免 Alembic 多個 head。
- 同一波次有多個 backend-developer Task 時（例如波次 4 的 T-007、T-011、T-018），可同時啟動多個 backend-developer subagent，各自在不同 worktree。
- 每個 Task 完成後的審查順序：Code Reviewer ∥ Security Reviewer（可平行）→ 修正 → QA（以 Story 為單位，在該 Story 最後一個 Task 合併後執行）。
- Story 驗收時點：US-001 於 T-012 後；US-013 於 T-010 + T-021 後；US-017 於 T-015 後；US-002 於 T-017 後；US-004 於 T-020 + T-022 後。

## 風險與相依

| # | 風險 | 影響 | 因應 |
|---|---|---|---|
| R1 | 基礎建設佔約 1/3 工作量，且關鍵路徑長達 11 個串行 Task，任何一個審查來回都會拖延 Demo | 高 | 關鍵路徑優先分派與審查；第 6 個工作天檢查進度，依「縮減順序」啟動縮減 |
| R2 | **Backlog 文件尚未進入 `main`**：Epic、Story、Task、規定文件目前只在 `chore/venue-regulations-research` 且未提交；從 `main` 開的 worktree 看不到 | 高 | 開始 T-001 前，先提交並合併本 branch 的文件到 `main` |
| R3 | SQLite `BEGIN IMMEDIATE` 與 pysqlite 隱式交易行為的相容問題；併發測試可能 flaky | 高 | T-004 先驗證寫鎖行為；T-018 併發測試需重複執行驗證穩定；ADR-003 明確記錄作法 |
| R4 | Server-side Session、CSRF 為自建機制，資安審查可能多次來回 | 中 | ADR-001/002 先經 Security Reviewer 審查（T-001 審查時即納入），再實作 T-007 |
| R5 | 時區處理錯誤（UTC 儲存 vs. Asia/Taipei 判斷日期、R-13 工作天） | 中 | ADR-004 統一規範；T-014 純函式以 AC 範例日期做參數化測試；「今天」一律由參數注入 |
| R6 | 樣板變數命名（`current_user`、`csrf_token`、flash 訊息）在 T-002、T-003、T-007、T-008 間不一致 | 中 | 由 T-001 routes.md 統一定義；T-002 寫入 style-guide |
| R7 | 共用檔案衝突：`tests/conftest.py`、`app/main.py` router 掛載會被多個平行 Task 修改 | 中 | 合併前 rebase 最新 `main`；conftest 以 fixture 分檔（`tests/fixtures/`）降低衝突 |
| R8 | R-13 工作天定義：**已由使用者決定**——本階段只算週一～週五，不考慮國定假日與補班 | 低 | T-014 不依賴假日資料；工作天數為單一來源常數，日後若需納入國定假日以新 Task 擴充 |
| R9 | 第一個 Sprint 無 Velocity 資料，估計不確定 | 中 | Sprint Review 記錄實際完成量，作為 Sprint 2 規劃依據 |

### 外部相依
- 無外部系統相依；容納人數資料取自 `docs/regulations/` 收費一覽表（無資料則留空）。
