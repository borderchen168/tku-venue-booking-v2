---
id: US-013
title: 使用者登入與登出
epic: EP-004
status: todo
priority: must
story_points: 5
sprint: sprint-01
created: 2026-11-06
---

# US-013 使用者登入與登出

## User Story(使用者故事)
身為學生或課外組承辦人，我想要以本機帳號安全地登入與登出系統，以便使用申請、審核、取消等需要身分的功能，且我的帳號不會被他人冒用。

## 驗收條件（Acceptance Criteria）
### AC1 成功登入
- Given 帳號 `412345678`（學生）已啟用，密碼正確
- When 使用者在登入頁輸入帳號密碼送出
- Then 登入成功，**重新產生 Session ID**，導向首頁並顯示使用者名稱與角色對應的選單（學生：我的申請、申請場地；承辦人：待審核、管理功能）；記錄登入成功的安全日誌

### AC2 登入失敗不透露帳號是否存在
- Given 帳號不存在，或帳號存在但密碼錯誤
- When 使用者送出登入
- Then 兩種情況都顯示相同訊息「帳號或密碼錯誤」，回應時間不應有明顯差異；記錄登入失敗的安全日誌（不記錄輸入的密碼）

### AC3 連續失敗鎖定（Rate Limit）
- Given 同一帳號在 15 分鐘內連續登入失敗 5 次
- When 第 6 次嘗試登入（即使密碼正確）
- Then 系統拒絕登入 15 分鐘，訊息仍不透露帳號是否存在；記錄鎖定事件

### AC4 停用帳號不能登入
- Given 帳號已被承辦人停用（US-014）
- When 使用者以正確密碼登入
- Then 顯示「帳號或密碼錯誤」，不建立 Session

### AC5 登出銷毀 Session
- Given 使用者已登入
- When 按下「登出」（POST 並帶 CSRF Token）
- Then 伺服器端 Session 被銷毀、Cookie 清除，使用舊 Session Cookie 再存取需登入的頁面時導向登入頁

### AC6 閒置逾時
- Given 使用者登入後閒置超過 30 分鐘（逾時值可由 `.env` 設定）
- When 再次存取需登入的頁面
- Then 導向登入頁並提示「登入已逾時，請重新登入」

### AC7 Cookie 安全屬性
- Given 使用者登入成功
- When 檢查回應的 Session Cookie
- Then 具備 `HttpOnly`、`SameSite=Lax`；正式環境（`.env` 環境別為 production）另具備 `Secure`

### AC8 登入表單 CSRF 防護
- Given 登入或登出請求缺少或帶錯誤的 CSRF Token
- When 送出
- Then 系統回應 403，不登入也不登出

### AC9 建立第一個承辦人帳號
- Given 系統剛部署，尚無任何帳號
- When 管理者執行管理指令（例如 `python -m app.cli create-staff`），依提示輸入帳號、姓名與密碼
- Then 建立一個承辦人帳號，密碼以 argon2 雜湊儲存；密碼少於 8 字元或屬常見密碼時拒絕建立

### AC10 輸入驗證
- Given 帳號為空、超過 50 字、或含白名單以外字元（僅允許英數字與 `._-`）
- When 送出登入
- Then 顯示「帳號或密碼錯誤」，不建立 Session，也不回應任何可推測帳號是否存在的資訊

## 商業規則與限制
- 角色：`student`（學生／社團負責人）、`staff`（課外組承辦人）。
- AGENTS.md 2.3 認證與 Session 規範（ASVS Level 2）。

## 假設
- 本機帳號，帳號格式為學號或職員編號；學生不能自行註冊。
- 鎖定門檻（15 分鐘內 5 次、鎖 15 分鐘）與閒置逾時（30 分鐘）為第一版預設值，可由 `.env` 調整。
- Sprint 1 的學生帳號與社團資料可先以管理指令建立，維護介面於 US-014 提供。

## 相依項目
- 無。

## 資安考量
- 權限：登入前只能存取公開頁面；需登入的 route 預設拒絕。
- 密碼：argon2 雜湊（`argon2-cffi`），禁止明碼或可逆加密；日誌不得記錄密碼、Session ID、CSRF Token。
- Session：登入後重新產生 Session ID（防 Session Fixation(會話固定)，CWE-384）；登出銷毀；閒置逾時。
- 輸入驗證：帳號長度與字元白名單；密碼長度上限（例如 128）防止雜湊 DoS。

## Task 清單
- [ ] T-001 系統架構、ERD、API 與路由設計
- [ ] T-002 頁面流程、base layout 與 CSS 規範
- [ ] T-003 專案骨架：FastAPI app、設定、日誌、錯誤處理與安全標頭
- [ ] T-004 DB 連線、PRAGMA 與交易工具
- [ ] T-005 Alembic 初始化與 Sprint 1 資料模型 migration
- [ ] T-007 Server-side Session 與 CSRF 機制
- [ ] T-008 認證服務與存取控制相依
- [ ] T-009 管理指令 CLI（建立承辦人、社團、學生）
- [ ] T-010 登入／登出頁面與 web route
- [ ] T-021 認證與 Session 安全負面測試

## DoR(就緒定義) 檢查
- [x] 使用者價值明確
- [x] 驗收條件完整且可測試
- [x] 已估點
- [x] 無未解決的相依項目
