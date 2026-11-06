---
id: US-007
title: 申請時上傳企畫書與場地配置文件
epic: EP-002
status: todo
priority: should
story_points: 5
sprint:
created: 2026-11-06
---

# US-007 申請時上傳企畫書與場地配置文件

## User Story(使用者故事)
身為社團負責人（學生），我想要在申請場地時直接上傳活動企畫書與場地配置文件，以便符合申請規定（R-10），承辦人也能在線上完成審核，不需另交紙本。

## 驗收條件（Acceptance Criteria）
### AC1 上傳必要附件後送出申請
- Given 學生已登入並填寫完申請表（US-004）
- When 他上傳「活動企畫書」1 個檔案（PDF，3 MB）與「場地配置文件」1 個檔案（PNG，1 MB）後送出
- Then 申請建立成功，明細頁列出兩個附件的顯示檔名、類型、大小

### AC2 缺少必要附件被拒絕（R-10）
- Given 學生填寫申請表
- When 未上傳企畫書或未上傳場地配置文件就送出
- Then 系統拒絕並提示「請上傳活動企畫書與場地配置文件」，不建立申請

### AC3 檔案類型白名單
- Given 允許的類型白名單為：**PDF（`.pdf`，`application/pdf`）、PNG（`.png`，`image/png`）、JPEG（`.jpg`／`.jpeg`，`image/jpeg`）**
- When 學生上傳 `.docx`、`.exe`、`.html`、`.svg`、`.zip`，或副檔名為 `.pdf` 但檔案內容（magic bytes 檔頭）不是 PDF 的檔案
- Then 系統拒絕該檔案並提示「僅接受 PDF、PNG、JPEG 檔案」，不儲存任何內容

### AC4 檔案大小上限
- Given 單一檔案上限為 **10 MB**、單筆申請附件總和上限為 **20 MB**
- When 學生上傳 12 MB 的 PDF，或總和超過 20 MB
- Then 系統拒絕並提示大小上限，且伺服器在讀取超過上限時即中止接收，不完整寫入磁碟

### AC5 空檔案被拒絕
- Given 學生上傳 0 byte 的檔案
- When 送出申請
- Then 系統拒絕並提示「檔案內容為空」

### AC6 申請人本人與承辦人可下載
- Given 申請 20 有附件
- When 申請人本人或承辦人點選附件
- Then 以 `Content-Disposition: attachment` 下載，並帶 `X-Content-Type-Options: nosniff`

### AC7 他人不能下載附件（IDOR）
- Given 申請 20 屬於學生「李小華」
- When 學生「王小明」或未登入訪客以網址直接存取申請 20 的附件
- Then 系統回應 404（未登入則導向登入頁），並記錄權限拒絕的安全日誌；公開頁面（US-002、US-003）不提供任何附件連結

### AC8 檔名安全處理
- Given 學生上傳的檔名為 `../../etc/passwd.pdf` 或含特殊字元
- When 系統儲存檔案
- Then 實際儲存檔名為系統產生的隨機名稱（例如 UUID），存放於 `.env` 設定的上傳目錄（不在 `app/static/` 下、不可被直接以 URL 存取）；原始檔名經清理後僅作顯示用途

## 商業規則與限制
- R-10：使用場地須附活動企畫書、場地配置文件。
- R-15：社團活動申請表由系統申請表單取代；經費預算表不在第一版範圍。
- 附件數量：企畫書 1 個、場地配置文件 1 個（皆必填）。

## 假設
- 採用附件上傳（README 第 4 節待釐清，第一版採用），白名單與大小上限如 AC3、AC4。
- 本 Story 完成後，附件成為 US-004 申請的必填項目；完成前送出的申請不追溯要求附件。
- 不提供退回補件（原 US-008 已取消）；附件需修正時，由社團重新送出新申請並重新上傳。
- 第一版不做防毒掃描（列為後續資安強化，需 Security Reviewer 評估）。

## 相依項目
- US-004、US-013。
- 上傳目錄路徑與大小上限需新增 `.env` 設定並同步 `.env.example`。

## 資安考量
- 權限：下載時於 service 層驗證為申請人本人或 `staff`（A01、CWE-639）。
- 輸入驗證：副檔名 + MIME + magic bytes 三者皆需符合白名單（CWE-434 不受限制的檔案上傳）；限制大小以防 DoS。
- 路徑：以 `pathlib.Path` 組合，隨機檔名，防止 Path Traversal(路徑穿越)（CWE-22）。
- 不在瀏覽器內以 inline 方式呈現使用者上傳的檔案，避免 XSS。

## Task 清單
- [ ] （由 Scrum Master 於 Sprint Planning 拆解）

## DoR(就緒定義) 檢查
- [x] 使用者價值明確
- [x] 驗收條件完整且可測試
- [x] 已估點
- [ ] 無未解決的相依項目（需 US-004、US-013）
