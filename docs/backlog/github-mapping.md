# Backlog 編號對照表（Markdown → GitHub Issues）

Backlog 已於 2026-11-07 遷移到 GitHub（IS-001），之後以 [GitHub Issues](https://github.com/borderchen168/tku-venue-booking-v2/issues) 與 [GitHub Project「淡江場地預約系統」](https://github.com/users/borderchen168/projects/2) 為唯一依據。
原 Markdown 檔已自 repo 移除，遷移前的版本可於 commit `52709d3` 查閱（IS-001～IS-003 於遷移時建立，只存在於 GitHub）。
本表由 `scripts/migrate_backlog.py` 產生，供文件與 ADR 中的舊編號對照使用。

| 舊編號 | 類型 | GitHub Issue | 標題 | 原始檔 |
|---|---|---|---|---|
| EP-001 | Epic | [#1](https://github.com/borderchen168/tku-venue-booking-v2/issues/1) | 場地與借用狀況查詢 | `docs/backlog/epics/EP-001-venue-availability-query.md` |
| EP-002 | Epic | [#2](https://github.com/borderchen168/tku-venue-booking-v2/issues/2) | 場地借用申請與審核 | `docs/backlog/epics/EP-002-booking-application-review.md` |
| EP-003 | Epic | [#3](https://github.com/borderchen168/tku-venue-booking-v2/issues/3) | 借用取消 | `docs/backlog/epics/EP-003-booking-cancellation.md` |
| EP-004 | Epic | [#4](https://github.com/borderchen168/tku-venue-booking-v2/issues/4) | 帳號、角色與社團 | `docs/backlog/epics/EP-004-account-role-club.md` |
| EP-005 | Epic | [#5](https://github.com/borderchen168/tku-venue-booking-v2/issues/5) | 場地與開放日期維護 | `docs/backlog/epics/EP-005-venue-schedule-maintenance.md` |
| EP-006 | Epic | [#6](https://github.com/borderchen168/tku-venue-booking-v2/issues/6) | 社團借用權利管理（停權） | `docs/backlog/epics/EP-006-club-booking-privilege.md` |
| US-001 | Story | [#7](https://github.com/borderchen168/tku-venue-booking-v2/issues/7) | 公開瀏覽場地清單與場地資訊 | `docs/backlog/stories/US-001-browse-venues.md` |
| US-002 | Story | [#8](https://github.com/borderchen168/tku-venue-booking-v2/issues/8) | 公開查看場地借用狀況 | `docs/backlog/stories/US-002-view-venue-availability.md` |
| US-003 | Story | [#9](https://github.com/borderchen168/tku-venue-booking-v2/issues/9) | 公開查詢借用紀錄 | `docs/backlog/stories/US-003-search-booking-records.md` |
| US-004 | Story | [#10](https://github.com/borderchen168/tku-venue-booking-v2/issues/10) | 學生線上申請臨時借用活動場地 | `docs/backlog/stories/US-004-apply-venue-booking.md` |
| US-005 | Story | [#11](https://github.com/borderchen168/tku-venue-booking-v2/issues/11) | 學生查看自己的申請與審核狀態 | `docs/backlog/stories/US-005-view-my-applications.md` |
| US-006 | Story | [#12](https://github.com/borderchen168/tku-venue-booking-v2/issues/12) | 承辦人審核借用申請（核准／駁回） | `docs/backlog/stories/US-006-review-application.md` |
| US-007 | Story | [#13](https://github.com/borderchen168/tku-venue-booking-v2/issues/13) | 申請時上傳企畫書與場地配置文件 | `docs/backlog/stories/US-007-upload-application-attachments.md` |
| US-009 | Story | [#14](https://github.com/borderchen168/tku-venue-booking-v2/issues/14) | 承辦人登錄學期固定借用（固定保留時段） | `docs/backlog/stories/US-009-register-fixed-bookings.md` |
| US-010 | Story | [#15](https://github.com/borderchen168/tku-venue-booking-v2/issues/15) | 借用同舟廣場時加借貴賓室 | `docs/backlog/stories/US-010-vip-room-add-on.md` |
| US-011 | Story | [#16](https://github.com/borderchen168/tku-venue-booking-v2/issues/16) | 學生取消自己的借用申請 | `docs/backlog/stories/US-011-student-cancel-application.md` |
| US-012 | Story | [#17](https://github.com/borderchen168/tku-venue-booking-v2/issues/17) | 承辦人取消已申請或已核准的借用 | `docs/backlog/stories/US-012-staff-cancel-booking.md` |
| US-013 | Story | [#18](https://github.com/borderchen168/tku-venue-booking-v2/issues/18) | 使用者登入與登出 | `docs/backlog/stories/US-013-login-logout.md` |
| US-014 | Story | [#19](https://github.com/borderchen168/tku-venue-booking-v2/issues/19) | 承辦人維護社團與學生帳號 | `docs/backlog/stories/US-014-manage-clubs-and-students.md` |
| US-015 | Story | [#20](https://github.com/borderchen168/tku-venue-booking-v2/issues/20) | 使用者變更密碼（含首次登入強制變更） | `docs/backlog/stories/US-015-change-password.md` |
| US-016 | Story | [#21](https://github.com/borderchen168/tku-venue-booking-v2/issues/21) | 承辦人維護場地資料 | `docs/backlog/stories/US-016-manage-venues.md` |
| US-017 | Story | [#22](https://github.com/borderchen168/tku-venue-booking-v2/issues/22) | 承辦人維護不開放日期與期間 | `docs/backlog/stories/US-017-manage-closed-dates.md` |
| US-018 | Story | [#23](https://github.com/borderchen168/tku-venue-booking-v2/issues/23) | 承辦人設定寒暑假開放時段 | `docs/backlog/stories/US-018-set-vacation-hours.md` |
| US-019 | Story | [#24](https://github.com/borderchen168/tku-venue-booking-v2/issues/24) | 承辦人設定與解除社團停權 | `docs/backlog/stories/US-019-suspend-club.md` |
| US-020 | Story | [#25](https://github.com/borderchen168/tku-venue-booking-v2/issues/25) | 承辦人登記未告知放棄使用並自動停權 | `docs/backlog/stories/US-020-record-no-show.md` |
| US-021 | Story | [#26](https://github.com/borderchen168/tku-venue-booking-v2/issues/26) | 應用程式層的登入 IP 頻率限制 | `docs/backlog/stories/US-021-login-ip-rate-limit.md` |
| US-022 | Story | [#27](https://github.com/borderchen168/tku-venue-booking-v2/issues/27) | 承辦人以 Web 介面解除帳號鎖定 | `docs/backlog/stories/US-022-staff-unlock-account.md` |
| T-001 | Task | [#28](https://github.com/borderchen168/tku-venue-booking-v2/issues/28) | 系統架構、ERD、API 與路由設計 | `docs/backlog/tasks/T-001-architecture-design.md` |
| T-002 | Task | [#29](https://github.com/borderchen168/tku-venue-booking-v2/issues/29) | 頁面流程、base layout 與 CSS 規範 | `docs/backlog/tasks/T-002-ui-design-base-layout.md` |
| T-003 | Task | [#30](https://github.com/borderchen168/tku-venue-booking-v2/issues/30) | 專案骨架：FastAPI app、設定、日誌、例外類別與時間工具 | `docs/backlog/tasks/T-003-app-skeleton-config.md` |
| T-004 | Task | [#31](https://github.com/borderchen168/tku-venue-booking-v2/issues/31) | DB 連線、PRAGMA 與交易工具 | `docs/backlog/tasks/T-004-db-connection-transaction.md` |
| T-005 | Task | [#32](https://github.com/borderchen168/tku-venue-booking-v2/issues/32) | Alembic 初始化與 Sprint 1 資料模型 migration | `docs/backlog/tasks/T-005-alembic-models-migration.md` |
| T-006 | Task | [#33](https://github.com/borderchen168/tku-venue-booking-v2/issues/33) | 場地初始資料 data migration | `docs/backlog/tasks/T-006-venue-seed-migration.md` |
| T-007 | Task | [#34](https://github.com/borderchen168/tku-venue-booking-v2/issues/34) | Server-side Session 與 CSRF 機制 | `docs/backlog/tasks/T-007-session-csrf.md` |
| T-008 | Task | [#35](https://github.com/borderchen168/tku-venue-booking-v2/issues/35) | 認證服務與存取控制相依 | `docs/backlog/tasks/T-008-auth-service-access-control.md` |
| T-009 | Task | [#36](https://github.com/borderchen168/tku-venue-booking-v2/issues/36) | 管理指令 CLI（建立承辦人、社團、學生） | `docs/backlog/tasks/T-009-admin-cli.md` |
| T-010 | Task | [#37](https://github.com/borderchen168/tku-venue-booking-v2/issues/37) | 登入／登出頁面與 web route | `docs/backlog/tasks/T-010-login-logout-pages.md` |
| T-011 | Task | [#38](https://github.com/borderchen168/tku-venue-booking-v2/issues/38) | 場地查詢 service | `docs/backlog/tasks/T-011-venue-query-service.md` |
| T-012 | Task | [#39](https://github.com/borderchen168/tku-venue-booking-v2/issues/39) | 場地清單與場地資訊頁 | `docs/backlog/tasks/T-012-venue-pages.md` |
| T-013 | Task | [#40](https://github.com/borderchen168/tku-venue-booking-v2/issues/40) | 不開放期間 service | `docs/backlog/tasks/T-013-closed-period-service.md` |
| T-014 | Task | [#41](https://github.com/borderchen168/tku-venue-booking-v2/issues/41) | R-13 工作天與最晚申請日計算 | `docs/backlog/tasks/T-014-workday-calculator.md` |
| T-015 | Task | [#42](https://github.com/borderchen168/tku-venue-booking-v2/issues/42) | 不開放期間管理頁 | `docs/backlog/tasks/T-015-closed-period-admin-pages.md` |
| T-016 | Task | [#43](https://github.com/borderchen168/tku-venue-booking-v2/issues/43) | 借用狀況週檢視查詢 service | `docs/backlog/tasks/T-016-availability-service.md` |
| T-017 | Task | [#44](https://github.com/borderchen168/tku-venue-booking-v2/issues/44) | 借用狀況週檢視頁 | `docs/backlog/tasks/T-017-availability-page.md` |
| T-018 | Task | [#45](https://github.com/borderchen168/tku-venue-booking-v2/issues/45) | 時段重疊檢查與 BEGIN IMMEDIATE 寫入 | `docs/backlog/tasks/T-018-booking-overlap-transaction.md` |
| T-019 | Task | [#46](https://github.com/borderchen168/tku-venue-booking-v2/issues/46) | 借用申請 service（規則驗證、授權、日誌） | `docs/backlog/tasks/T-019-booking-application-service.md` |
| T-020 | Task | [#47](https://github.com/borderchen168/tku-venue-booking-v2/issues/47) | 借用申請表單與送出結果頁 | `docs/backlog/tasks/T-020-booking-application-pages.md` |
| T-021 | Task | [#48](https://github.com/borderchen168/tku-venue-booking-v2/issues/48) | 認證與 Session 安全負面測試 | `docs/backlog/tasks/T-021-auth-security-tests.md` |
| T-022 | Task | [#49](https://github.com/borderchen168/tku-venue-booking-v2/issues/49) | 申請規則、併發與 Sprint Demo 端到端測試 | `docs/backlog/tasks/T-022-booking-rules-demo-e2e-tests.md` |
| T-023 | Task | [#50](https://github.com/borderchen168/tku-venue-booking-v2/issues/50) | HTTP 安全中介層、表單限制與統一錯誤處理 | `docs/backlog/tasks/T-023-http-security-middleware-errors.md` |
| IS-001 | Issue | [#51](https://github.com/borderchen168/tku-venue-booking-v2/issues/51) | 遷移到 GitHub：Repo、Project 與 Backlog | `docs/backlog/issues/IS-001-github-migration.md` |
| IS-002 | Issue | [#52](https://github.com/borderchen168/tku-venue-booking-v2/issues/52) | 建立 GitHub Actions CI | `docs/backlog/issues/IS-002-ci.md` |
| IS-003 | Issue | [#53](https://github.com/borderchen168/tku-venue-booking-v2/issues/53) | 建立 CD：部署到本機 self-hosted runner | `docs/backlog/issues/IS-003-cd.md` |
