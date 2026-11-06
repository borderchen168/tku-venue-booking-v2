---
id: T-003
title: 專案骨架：FastAPI app、設定、日誌、錯誤處理與安全標頭
story: [US-013, US-001, US-017, US-002, US-004]
status: todo        # todo / in-progress / review / done / blocked
assignee: backend-developer
branch: feature/T-003-app-skeleton-config
sprint: sprint-01
depends_on: [T-001]
created: 2026-11-06
---

# T-003 專案骨架：FastAPI app、設定、日誌、錯誤處理與安全標頭

## 說明
建立可啟動的 FastAPI 應用程式與共用基礎設施：設定讀取、日誌、Jinja2 環境、統一錯誤處理、HTTP 安全標頭，以及鎖定版本的相依套件檔案與測試基礎。

## 完成條件
- [ ] 以 pip-tools 產生 `requirements.lock`、`requirements-dev.lock` 並提交；`python -m pip_audit -r requirements.lock` 無已知漏洞。
- [ ] `app/core/config.py`：`Settings`（`pydantic-settings`）讀取 `.env.example` 所列全部設定；`APP_ENV` 為列舉白名單；production 環境下 `SECRET_KEY` 為範例值或長度不足時啟動失敗。
- [ ] `app/core/logging.py`：統一 logger 設定與安全事件 logger（`security`），提供記錄事件的 helper，禁止記錄密碼、Token、Session ID。
- [ ] `app/main.py`：`create_app()` 工廠函式、掛載 `app/static/`、router 掛載點、健康檢查 `GET /healthz`。
- [ ] Jinja2 `Jinja2Templates` 設定於共用模組，**autoescape 開啟**，並提供注入 `current_user`、`csrf_token` 等 context 的擴充點（實際值由 T-007、T-008 提供）。
- [ ] 統一錯誤處理：404/403/422/500 以 T-002 錯誤頁呈現（T-002 未合併前可用簡易 fallback）；非 debug 模式不回傳 stack trace 或內部錯誤細節。
- [ ] 安全標頭 middleware：`Content-Security-Policy`（`default-src 'self'`，不允許 inline script）、`X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`、`Referrer-Policy: strict-origin-when-cross-origin`。
- [ ] `tests/conftest.py`：以 `tmp_path` 建立測試用 `Settings`（`APP_ENV=test`）與 `TestClient` fixture。
- [ ] 測試：設定驗證（含 production 弱 `SECRET_KEY` 失敗）、安全標頭存在、500 時不洩漏細節、`/healthz` 回應 200。
- [ ] 若新增設定，同步更新 `.env.example`。

## 技術備註
- 跨平台：路徑一律 `pathlib.Path`（以 `Path(__file__).resolve().parent` 定位 templates/static），`open()` 指定 `encoding='utf-8'`。
- 不實作 Session、CSRF（T-007）與 DB（T-004）。
- 可與 T-002 平行進行。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過（安全標頭、錯誤處理、秘密管理）
- [ ] QA 驗收通過
- [ ] 文件與 .env.example 已更新
