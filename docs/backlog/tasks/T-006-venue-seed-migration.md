---
id: T-006
title: 場地初始資料 data migration
story: US-001
status: todo        # todo / in-progress / review / done / blocked
assignee: dba
branch: feature/T-006-venue-seed-migration
sprint: sprint-01
depends_on: [T-005]
created: 2026-11-06
---

# T-006 場地初始資料 data migration

## 說明
以 Alembic data migration 匯入 8 個初始場地（US-001 假設、EP-005 範圍），供公開頁面與申請功能使用。

## 完成條件
- [ ] 新增 data migration，匯入：學生活動中心、驚聲廣場、同舟廣場、覺軒花園教室、五虎崗舞蹈教室、體育館 1 樓、B1 社辦廣場（類別：社團活動場地），海報街（類別：擺攤場地）。全部為啟用中。
- [ ] 容納人數參考 `docs/regulations/淡水校園_115各類場地及設備器材借用維護費收費一覽表.pdf`，無資料者留空（NULL）；說明欄可填簡短描述。
- [ ] 同舟廣場貴賓室**不**建立為獨立場地（US-010 處理）。
- [ ] migration 以參數化 insert（`op.bulk_insert` 或 `sa.table` 定義），不依賴 ORM model 類別（避免日後 model 變更造成舊 migration 失效）；`downgrade` 只刪除本 migration 匯入的資料。
- [ ] 測試：`upgrade head` 後有 8 筆啟用中場地、類別正確；`downgrade` 一步後資料移除。

## 技術備註
- 接在 T-005 之後，`down_revision` 指向 T-005 的 revision，維持單一 head。

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
