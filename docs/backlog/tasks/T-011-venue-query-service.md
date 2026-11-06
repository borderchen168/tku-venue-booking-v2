---
id: T-011
title: 場地查詢 service
story: US-001
status: todo        # todo / in-progress / review / done / blocked
assignee: backend-developer
branch: feature/T-011-venue-query-service
sprint: sprint-01
depends_on: [T-005]
created: 2026-11-06
---

# T-011 場地查詢 service

## 說明
提供公開場地清單與單一場地查詢的 repository、service 與 Pydantic schema，供 US-001 頁面、US-002 借用狀況與 US-004 申請檢查共用。

## 完成條件
- [ ] `app/repositories/venue_repository.py`：列出啟用中場地（依類別、名稱排序）、依 id 取得場地。
- [ ] `app/services/venue_service.py`：`list_active_venues()` 依類別分組；`get_active_venue(venue_id)` 停用或不存在時拋出統一的 NotFound 例外（由 router 轉為 404，US-001 AC3、AC4）。
- [ ] `app/schemas/venue.py`：公開輸出 schema，只含名稱、類別、容納人數（可為 None）、說明、可借用時段（R-01：08:00–22:00，由設定或常數提供，不寫死於樣板）。
- [ ] 單元測試：只回傳啟用中場地、分組與排序、停用與不存在皆為 NotFound。

## 技術備註
- R-01 開放時段請定義為單一來源（例如 `app/core/` 常數或設定），T-016、T-019 共用。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（如適用）
- [ ] QA 驗收通過
- [ ] 文件與 .env.example 已更新
