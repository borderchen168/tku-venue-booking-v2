# Sprint 01 Planning(衝刺規劃)

- 期間：2026-11-09 ~ 2026-11-20（兩週，10 個工作天）
- Sprint Goal(衝刺目標)：**建立可執行、符合資安規範的系統基礎，並完成第一條端到端流程——訪客可查看場地與借用狀況、承辦人可設定不開放期間、學生登入後能以社團名義送出符合規定的借用申請，且不合規的申請一律被拒絕。**

## 範圍評估

### 結論：採用 PO 建議的 5 個 Story（25 點），不刪減 Story，但預先約定縮減順序

| 項目 | 評估 |
|---|---|
| 功能 Story | 25 點（US-013、US-001、US-017、US-002、US-004） |
| 基礎建設 | repo 只有骨架，需額外完成架構設計、app 骨架與設定、HTTP 安全中介層、DB 連線與交易工具、Alembic 與資料模型、base layout、Session / CSRF、認證服務等 9 個 Task（T-001～T-008、T-023），工作量約相當於 9～11 點 |
| 合計 | 約 34～36 點等價工作量；第一個 Sprint 沒有歷史 Velocity(速度) 可參考 |

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
| 4 | 學期暫定每年 9/1～12/31、3/1～6/30 | T-001（ADR-006 學期區間設定方式）、T-019：學期區間以外的日期一律拒絕（US-004 AC17，本 Sprint 實作） |

## Task 拆解與分派

| Task | 標題 | Story | 負責角色 | 相依 | 可平行 |
|---|---|---|---|---|---|
| T-001 | 系統架構、ERD、API 與路由設計 | 全部 | system-analyst | — | 否（第一個） |
| T-002 | 頁面流程、base layout 與 CSS 規範 | 全部 | ui-ux-designer | T-001 | 與 T-003 平行 |
| T-003 | 專案骨架：FastAPI app、設定、日誌、例外類別與時間工具 | 全部 | backend-developer | T-001 | 與 T-002 平行 |
| T-023 | HTTP 安全中介層、表單限制與統一錯誤處理（自 T-003 拆出） | 全部 | backend-developer | T-003 | 與 T-002、T-004、T-014 平行 |
| T-004 | DB 連線、PRAGMA 與交易工具 | 全部 | backend-developer | T-003 | 與 T-002、T-014、T-023 平行 |
| T-005 | Alembic 初始化與 Sprint 1 資料模型 migration | 全部 | dba | T-001, T-004 | 與 T-002、T-014、T-023 平行 |
| T-006 | 場地初始資料 data migration | US-001 | dba | T-005 | 與 T-007、T-011、T-018 平行 |
| T-007 | Server-side Session 與 CSRF 機制 | US-013 | backend-developer | T-003, T-005, T-023 | 與 T-006、T-011、T-018 平行 |
| T-008 | 認證服務與存取控制相依 | US-013 | backend-developer | T-005, T-007 | 與 T-012 平行 |
| T-009 | 管理指令 CLI（建立承辦人、社團、學生） | US-013, US-004 | backend-developer | T-008 | 與 T-010、T-013 平行 |
| T-010 | 登入／登出頁面與 web route | US-013 | frontend-developer | T-002, T-008 | 與 T-009、T-013 平行 |
| T-011 | 場地查詢 service | US-001 | backend-developer | T-005 | 與 T-006、T-007、T-018 平行 |
| T-012 | 場地清單與場地資訊頁 | US-001 | frontend-developer | T-002, T-006, T-011, T-023 | 與 T-008 平行 |
| T-013 | 不開放期間 service | US-017 | backend-developer | T-005, T-008, T-018 | 與 T-009、T-010 平行 |
| T-014 | R-13 工作天與最晚申請日計算（純函式，只算週一～週五；另含學期區間 `is_in_semester`） | US-004 | backend-developer | T-003 | 可提早做，與 T-004～T-013、T-023 平行 |
| T-015 | 不開放期間管理頁 | US-017 | frontend-developer | T-002, T-010, T-013 | 與 T-016、T-019、T-021 平行 |
| T-016 | 借用狀況週檢視查詢 service | US-002 | backend-developer | T-011, T-013, T-014, T-018 | 與 T-015、T-019、T-021 平行 |
| T-017 | 借用狀況週檢視頁 | US-002 | frontend-developer | T-002, T-012, T-016 | 與 T-019 平行 |
| T-018 | 時段重疊檢查與 BEGIN IMMEDIATE 寫入 | US-004 | backend-developer | T-004, T-005 | 與 T-006、T-007、T-011 平行 |
| T-019 | 借用申請 service（規則驗證、授權、日誌） | US-004 | backend-developer | T-008, T-009, T-011, T-013, T-014, T-018 | 與 T-015、T-016、T-017 平行 |
| T-020 | 借用申請表單與送出結果頁 | US-004 | frontend-developer | T-010, T-017, T-019 | 否 |
| T-021 | 認證與 Session 安全負面測試 | US-013 | tester | T-009, T-010, T-012 | 與 T-015～T-020 平行 |
| T-022 | 申請規則、併發與 Sprint Demo 端到端測試 | US-004, US-002, US-017, US-001 | tester | T-009, T-015, T-020 | 否（最後） |

Task 檔案：`docs/backlog/tasks/T-001-*.md` ～ `T-023-*.md`（T-023 為 2026-11-06 自 T-003 拆出，編號接續，執行順序位於波次 2）。

## 建議執行順序（波次）

同一波次內的 Task 可平行，各自在獨立 worktree 進行；前一波次的相依 Task 須**已 squash merge 回 `main`** 才開始下一個。

| 波次 | Task | 說明 |
|---|---|---|
| 0 | T-001 | SA 設計先行（ERD、routes、ADR），其餘全部依此 |
| 1 | T-002 ∥ T-003 | UI 規範 / base layout 與 app 骨架平行 |
| 2 | T-004 ∥ T-014 ∥ T-023 | DB 連線（關鍵路徑）；工作天純函式；HTTP 安全中介層與錯誤處理（**須於 T-007 開始前合併**，可容許延誤至 T-005 合併為止） |
| 3 | T-005 | 資料模型與初始 migration（關鍵路徑） |
| 4 | T-006 ∥ T-007 ∥ T-011 ∥ T-018 | 場地資料、Session/CSRF、場地 service、重疊交易 |
| 5 | T-008 ∥ T-012 | 認證服務；場地公開頁（**US-001 可在此波次先完成驗收**） |
| 6 | T-009 ∥ T-010 ∥ T-013 | CLI、登入頁（**US-013 功能完成**）、不開放期間 service |
| 7 | T-015 ∥ T-016 ∥ T-019 ∥ T-021 | 管理頁（**US-017 完成**）、借用狀況 service、申請 service、認證安全測試 |
| 8 | T-017 | 借用狀況頁（**US-002 完成**） |
| 9 | T-020 | 申請頁（**US-004 功能完成**） |
| 10 | T-022 | 端到端與 Demo 驗收測試（含 `EXPECTED_POST_PATHS` 最終驗收），之後 QA 對全部 Story 驗收 |

**關鍵路徑(Critical Path)**：T-001 → T-003 → T-004 → T-005 → T-007 → T-008 → T-013 → T-016 → T-017 → T-020 → T-022（11 個 Task 串行；串行順序不變，但 T-003 拆分後工作量縮小，關鍵路徑實際長度縮短）。
關鍵路徑上的 Task 應優先分派並優先審查；非關鍵路徑（T-002、T-006、T-011、T-012、T-014、T-018、T-021、T-023）用來填滿平行空檔。

> 2026-11-06 依 T-001 設計同步 Task 後，新增相依 T-018 → T-013、T-014 / T-018 → T-016、T-009 → T-019，皆指向較早的波次，**波次與關鍵路徑不變**。
> 但 **T-009 變為次關鍵路徑**（T-008 → T-009 → T-019 → T-020，與關鍵路徑同樣在波次 9 匯合），T-009 延誤會直接延後 T-019；**T-018 須於波次 4 準時合併**，否則同時卡住 T-013 與 T-016。
>
> 2026-11-06 依 T-001 **第 3 版**設計再次同步：
> - **T-003 拆分為 T-003（骨架、設定、日誌、例外、時間工具）與 T-023（HTTP 安全中介層、表單限制、統一錯誤處理）**。理由：第 3 版再為 T-003 加入 `FormContentTypeMiddleware`、`app/core/forms.py`、chunked 413 與回應中止邏輯、路由前純文字回應、`FORBIDDEN_SECRET_KEYS` 等，明顯超過 1 天原則（R11）；而 T-004、T-014 只需要 `config` / `exceptions`，真正需要中介層的是 T-007 與 web Task。拆分後 T-023 與 T-004、T-014 同在波次 2，**有 T-004 + T-005 兩個 Task 的時間餘裕**，不在關鍵路徑上；關鍵路徑上的 T-003 變小。
> - 新增相依：T-023 → T-007（middleware 掛載位置、`LimitedFormRoute`、`CSRFError` handler）、T-023 → T-012（route class、404 / 422 handler）、T-012 → T-021（「登入飽和時 `GET /venues` 仍可回應」測試）。皆指向較早波次，**波次數與關鍵路徑串行順序不變**。
> - T-008 為避免相依 T-010 / T-012（會拉長關鍵路徑），「登入飽和」測試以測試專用 route 驗證機制，T-021 以實際 route 重跑。
>
> 2026-11-06 依 T-001 **第 4 版**設計與最終複審（NB-1～NB-6）同步：
> - T-023 新增 `ALL_ROUTERS`（`app/routers/__init__.py`，`create_app` 唯一掛載來源）、`iter_api_routes` 與 `tests/integration/test_route_coverage.py`（`EXPECTED_POST_PATHS` 起始為空）、`SAFE_METHODS`、`RETRY_AFTER_SECONDS`。T-010 / T-012 / T-015 / T-017 / T-020 把 router 加入 `ALL_ROUTERS`，T-010 / T-015 / T-020 擴充 `EXPECTED_POST_PATHS`。
> - **web Task 對 T-023 的相依**：T-012 原已直接相依；T-010、T-015、T-020 經 T-008 → T-007 → T-023，T-017 經 T-012 → T-023 間接相依，**不新增 depends_on、波次不變**。
> - **`EXPECTED_POST_PATHS` 最終驗收改由 T-022 負責**（Orchestrator 採用 R17 替代方案）：「等於 routes.md 6 條 POST 路徑」需等 T-015、T-020 合併，若留在 T-021 會迫使 T-021 移到波次 10。改為 T-021 留在波次 7，只驗證當時已掛載的每個 POST 未帶 Token 回 403、每個 route 都是 `LimitedFormRoute`；最終清單相等由 T-022（原本就相依 T-015、T-020）驗收。**T-021 depends_on 不變、波次與關鍵路徑不變**。

### 分派原則

- **DBA 是唯一撰寫 migration 的角色**（T-005、T-006 串行），其他 Task 若需要 schema 變更，回報 Orchestrator 改派 DBA，避免 Alembic 多個 head。
- 同一波次有多個 backend-developer Task 時（例如波次 2 的 T-004、T-014、T-023，波次 4 的 T-007、T-011、T-018），可同時啟動多個 backend-developer subagent，各自在不同 worktree。
- 波次 2 的 T-004 與 T-023 都會修改 `app/main.py` / `tests/fixtures/`，後合併者需 rebase；建議 T-004 先合併（關鍵路徑）。
- 每個 Task 完成後的審查順序：Code Reviewer ∥ Security Reviewer（可平行）→ 修正 → QA（以 Story 為單位，在該 Story 最後一個 Task 合併後執行）。
- Story 驗收時點：US-001 於 T-012 後；US-013 於 T-010 + T-021 後（波次 7）；US-017 於 T-015 後；US-002 於 T-017 後；US-004 於 T-020 + T-022 後。

## 風險與相依

| # | 風險 | 影響 | 因應 |
|---|---|---|---|
| R1 | 基礎建設佔約 1/3 工作量，且關鍵路徑長達 11 個串行 Task，任何一個審查來回都會拖延 Demo | 高 | 關鍵路徑優先分派與審查；第 6 個工作天檢查進度，依「縮減順序」啟動縮減 |
| R2 | ~~Backlog 文件尚未進入 `main`~~ | — | **已解決**：已於 commit `ac9f9a0` 合併到 `main` |
| R3 | SQLite `BEGIN IMMEDIATE` 與 pysqlite 隱式交易行為的相容問題；併發測試可能 flaky | 高 | T-004 先驗證寫鎖行為；T-018 併發測試需重複執行驗證穩定；ADR-003 明確記錄作法 |
| R4 | Server-side Session、CSRF 為自建機制，資安審查可能多次來回 | 中 | ADR-001/002 已於 T-001 第 2、3 版納入 Code Review 與 Security Review 意見；T-007 依 ADR 完成條件實作並附完整負面測試 |
| R5 | 時區處理錯誤（UTC 儲存 vs. Asia/Taipei 判斷日期、R-13 工作天） | 中 | ADR-004 統一規範；T-014 純函式以 AC 範例日期做參數化測試；「今天」一律由參數注入 |
| R6 | 樣板變數命名（`current_user`、`csrf_token`、flash 訊息）在 T-002、T-003、T-007、T-008 間不一致 | 中 | 由 T-001 routes.md 統一定義；T-002 寫入 style-guide |
| R7 | 共用檔案衝突：`tests/conftest.py`、`app/main.py` router 掛載會被多個平行 Task 修改 | 中 | 合併前 rebase 最新 `main`；conftest 以 fixture 分檔（`tests/fixtures/`）降低衝突 |
| R8 | R-13 工作天定義：**已由使用者決定**——本階段只算週一～週五，不考慮國定假日與補班 | 低 | T-014 不依賴假日資料；工作天數為單一來源常數，日後若需納入國定假日以新 Task 擴充 |
| R9 | 第一個 Sprint 無 Velocity 資料，估計不確定 | 中 | Sprint Review 記錄實際完成量，作為 Sprint 2 規劃依據 |
| R10 | **T-007 自建無狀態登入前 CSRF Token（nonce Cookie ＋ HMAC，ADR-002 第 4 節）**：第 3 版再增加 `app/core/cookies.py`（Cookie 設定 / 刪除唯一入口）、`app/core/keys.py`（`derive_key`）、nonce 改 `SameSite=Lax` 並每次刷新、`no_nonce` reason、`pop_flashes` 無 flash 不寫入、略過 `/static` 與 `/healthz`；多一組自建密碼學邏輯，`SECRET_KEY` 成為必要秘密；T-007 工作量與審查負擔再增加，且位於關鍵路徑 | 中→高 | ADR-002 已定 Token 格式、金鑰衍生與驗證步驟，開發者不需自行設計；表單限制已移到 T-023，T-007 不必處理；T-007 必須涵蓋竄改 / 換 nonce / 過期 / 格式錯誤 / Cookie 刪除屬性測試，T-021 獨立再驗證（含多分頁＋外站連入）；`SECRET_KEY` 強度與 `FORBIDDEN_SECRET_KEYS` 由 T-003 強制；若 T-007 預估超過 1.5 天，可把 `cookies.py` / `keys.py` / 登入前 Token 拆為獨立 Task（與 Session 部分平行） |
| R11 | ~~T-003 範圍膨脹~~：第 3 版再加入 `FormContentTypeMiddleware`、`forms.py`、chunked 413 中止邏輯等 | 高→中 | **已處理**：2026-11-06 拆為 T-003 ＋ T-023（見上方同步說明）。殘餘風險：T-023 若延誤超過 T-005 合併時點，會直接卡住 T-007（關鍵路徑）；Orchestrator 在 T-005 開始時檢查 T-023 進度 |
| R12 | **共用型別擁有者調整**（`timeutils`、`to_field_errors`、全部例外 → T-003；`UTCDateTime` → T-005；`semester.py` → T-014；`CurrentUser`、`SessionStore` → T-007；`club_repository` → T-009）：先做的 Task 若未依設計簽章建立，平行 Task 會衝突或重複定義 | 中 | 以 overview.md 3.1 為唯一依據；後續 Task 只能新增、不可改既有簽章，需改時回報 Orchestrator；Code Review 檢查 |
| R13 | **寫入交易通則**（ADR-003 2.1：所有寫入以 `immediate_transaction` 開始，違反前置條件即 `RuntimeError`）影響 T-007、T-008、T-009、T-013、T-018、T-019；開發者不熟悉時易在審查中來回 | 中 | T-004 先提供 SQL 記錄 fixture 與範例測試；`SAWarning` 視為錯誤；Code Review 以 ADR-003 2.1 一覽表逐項檢查 |
| R14 | 新增的併發測試（T-008 20 執行緒 × 10 輪、T-018 8 執行緒 × 20 輪、T-021 / T-022 HTTP 併發）可能 flaky 或拖慢測試時間 | 中 | 使用 `threading.Barrier` 與各自 DB Session；測試期間使用 `cheap_password_service`；若單次 `pytest` 明顯變慢，可為併發測試加 marker 但不得排除於 DoD 之外 |
| R15 | **設計文件的模組擁有者仍標示 T-003**：overview.md 3.1 / 3.2、error-handling.md、ADR-002 2.1 把 `middleware.py`、`forms.py`、`error_handlers.py` 列為 T-003；拆分後實際為 T-023，開發者可能依設計文件誤判範圍 | 低 | T-003、T-023 檔案已明文說明對照；請 SA 下次修訂時同步 overview.md 3.1 / 3.2 擁有者欄位 |
| R16 | **T-008 範圍增加**（關鍵路徑）：`normalize_username`、不等待的雜湊名額、兩條清理路徑、rehash 條件式更新、登入飽和測試；且「登入飽和時 `GET /venues` 仍可回應」測試需要多執行緒 + 時間斷言，易 flaky | 中 | ADR-005 已給完整流程與測試規格；T-008 以測試專用 route 驗證機制、T-021 用實際 route 重跑；飽和測試以寬鬆時間門檻（1 秒）並可加 marker，但不得排除於 DoD 之外（同 R14） |
| R17 | ~~T-021 需移到波次 10 才能驗收 `EXPECTED_POST_PATHS` 最終清單~~ | — | **已解決**（2026-11-06）：最終清單驗收移到 T-022，T-021 留在波次 7，排程不變 |

### 外部相依
- 無外部系統相依；容納人數資料取自 `docs/regulations/` 收費一覽表（無資料則留空）。
