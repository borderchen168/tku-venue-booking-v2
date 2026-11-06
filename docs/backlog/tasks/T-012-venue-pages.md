---
id: T-012
title: 場地清單與場地資訊頁
story: US-001
status: todo        # todo / in-progress / review / done / blocked
assignee: frontend-developer
branch: feature/T-012-venue-pages
sprint: sprint-01
depends_on: [T-002, T-006, T-011]
created: 2026-11-06
---

# T-012 場地清單與場地資訊頁

## 說明
實作公開（不需登入）的場地清單頁與場地資訊頁，完成 US-001。

## 完成條件
- [ ] `GET /venues`：依類別（社團活動場地、擺攤場地）列出啟用中場地，未登入回應 200（AC1）。
- [ ] `GET /venues/{venue_id}`：顯示名稱、類別、容納人數（未設定顯示「未提供」）、說明、可借用時段 08:00–22:00，並提供前往借用狀況頁的連結（AC2；連結路徑依 T-001 routes.md，頁面於 T-017 實作）。
- [ ] `venue_id` 以 FastAPI 路徑參數驗證為正整數；停用、不存在、格式錯誤回應 404 / 422 並以統一錯誤頁呈現（AC3、AC4）。
- [ ] 場地說明經 autoescape 輸出，不使用 `|safe`。
- [ ] 整合測試：AC1～AC4，含停用場地不出現在清單、直接存取回應 404、XSS 字串被跳脫。

## 技術備註
- 可寫入：`app/templates/`、`app/static/`、`app/routers/web/`、`tests/`。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（如適用）
- [ ] QA 驗收通過（US-001）
- [ ] 文件與 .env.example 已更新
