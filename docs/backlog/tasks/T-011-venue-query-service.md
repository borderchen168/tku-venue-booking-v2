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
本 Task 是 `app/core/constants.py`（R-01 開放時段）與 `PublicVenue`、`VenueCategoryGroup` 的負責 Task（overview.md 3.1）。

## 完成條件
- [ ] `app/repositories/venue_repository.py`：列出啟用中場地，**排序為 `category, sort_order, name`**（erd.md 3.4，使用 `venues.sort_order`）；依 id 取得場地。
- [ ] `app/services/venue_service.py`：`list_active_venues()` 依類別分組（`VenueCategoryGroup`）；`get_active_venue(venue_id)` 停用或不存在時拋 `NotFoundError`（T-003 建立類別，由 T-023 的全域 handler 轉 404，US-001 AC3、AC4）；查詢使用預設 deferred 唯讀交易（ADR-003 2.1）。
- [ ] `app/schemas/venue.py`：`PublicVenue`（只含公開欄位：id、名稱、類別、容納人數（可為 None）、說明、可借用時段）與 `VenueCategoryGroup`。
- [ ] `app/core/constants.py`：`OPEN_TIME`（08:00）、`CLOSE_TIME`（22:00）、`SLOT_MINUTES`（30），作為 R-01 單一來源（overview.md 第 5 節），供 T-016、T-019、T-020 使用。
- [ ] 單元測試：只回傳啟用中場地、分組與 `sort_order` 排序（同類別內 `sort_order` 優先於名稱）、停用與不存在皆為 `NotFoundError`、輸出 schema 不含非公開欄位。

## 技術備註
- `routers` 透過 `routers/deps.py` 的 `get_venue_service` 工廠取得 service（overview.md 2.1），本 Task 一併新增該工廠。
- 中文名稱以 code point 排序不直覺，因此以 `sort_order` 控制顯示順序（值由 T-006 匯入）。

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
