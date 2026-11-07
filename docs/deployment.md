# 部署與啟動說明

- 對應 Task：T-003（啟動參數、設定檢查）；依據：`docs/architecture/overview.md` 第 4、7 節、`docs/architecture/security-logging.md`
- 最後更新：2026-11-07

## 1. 本機開發

環境建立見 `AGENTS.md` 第 4 節。啟動：

```bash
python -m alembic upgrade head        # T-004 / T-005 完成後可用（目前尚無 migration）
python -m uvicorn app.main:app --reload --no-server-header
```

- `--no-server-header`：**必要參數**，不輸出 `Server` 標頭（overview.md 第 7、8 節）。開發與正式環境都要加。
- `app.main:app` 於第一次被 Uvicorn 存取時才以 `.env` 建立；也可用 `python -m uvicorn app.main:create_app --factory --no-server-header`。
- 健康檢查：`GET /healthz` → `200 text/plain` `ok`（不含版本或 DB 資訊）。
- `/docs`、`/redoc`、`/openapi.json` 已關閉（404）。

## 2. 正式環境設定（`.env`）

`APP_ENV=production` 時，下列任一項不符即**啟動失敗**（`app/core/config.py`）：

| 設定 | 要求 |
|---|---|
| `APP_DEBUG` | `false` |
| `SECRET_KEY` | 長度 ≥ 32、前後不可有空白、至少 10 種不同字元（`secrets.token_hex()` 也可通過），且不是 `FORBIDDEN_SECRET_KEYS`（`change-me`、`.env.example` 範例值）；建議以 `python -c "import secrets; print(secrets.token_urlsafe(64))"` 產生（任何環境都不可為空） |
| `SESSION_COOKIE_NAME` | 以 `__Host-` 開頭（例如 `__Host-tku_session`） |
| `SESSION_COOKIE_SECURE` | `true`（`__Host-` 名稱在任何環境都要求 `true`） |
| `ALLOWED_HOSTS` | 不可為空；**只能填完整主機名稱**（例如 `venue.tku.edu.tw`），逗號分隔。任何含 `*` 的項目（`*`、`*.tku.edu.tw`）都會被拒絕 |

`.env` **只放 `Settings` 的欄位**（`extra='forbid'`）：出現 `Settings` 沒有的鍵（例如拼錯 `SESSION_COOKIE_SECUR`）在任何環境都會啟動失敗。Uvicorn 的參數（例如 `FORWARDED_ALLOW_IPS`）請用命令列參數或另外設定的環境變數，**不要**寫進 `.env`。

設定錯誤訊息（`str(exc)`）只列出鍵名，不會輸出 `SECRET_KEY` 等原始值。程式中若要記錄 `ValidationError`，一律使用 `exc.errors(include_input=False, include_context=False)`：`hide_input_in_errors` 只遮蔽 `str()`，`exc.errors()` 預設仍含原始輸入。

## 3. 正式環境啟動

安裝（只裝執行期相依，並驗證 hash）：

```bash
python -m pip install --require-hashes -r requirements.lock
python -m pip install -e . --no-deps        # 需在上一行之後、分開執行（本專案本身沒有 hash）
python -m alembic upgrade head              # T-004 / T-005 完成後可用
```

啟動：

```bash
python -m uvicorn app.main:app --no-server-header --host 127.0.0.1 --port 8000
```

- 前置**反向代理**負責 TLS 終結，並對 `POST /login` 設定以 IP 為鍵的頻率限制（例如每 IP 每分鐘 10 次，overview.md 第 7 節）。
- 若啟用 `--proxy-headers`，`--forwarded-allow-ips`（或 `FORWARDED_ALLOW_IPS`）**必須**為代理的實際 IP，**不得為 `*`**。
- SQLite 檔案不可放在網路檔案系統上。
- **記憶體**：雜湊峰值 ≈ Uvicorn worker 數 × `PASSWORD_HASH_CONCURRENCY` × 64 MiB（預設 1 worker 約 256 MiB），主機需預留。

## 4. 日誌

- `app`：一般程式日誌（訊息中的換行與控制字元會被跳脫，traceback 另外附加）；`security`：安全事件，單行 JSON（security-logging.md）。兩者輸出到 stderr，等級由 `LOG_LEVEL` 控制，由程序管理器收集。
- 告警規則（帳號重複鎖定、大量鎖定、權限探測、登入忙碌、CSRF 異常）見 security-logging.md 2.1，接上日誌監控時設定。
