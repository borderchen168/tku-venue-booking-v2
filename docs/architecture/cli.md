# 管理指令 CLI 規格

- 對應 Task：T-009；Story：US-013 AC9、US-004（Demo 資料）
- 最後更新：2026-11-06（第 3 版：帳號一律經 `normalize_username()`、日誌加 `os_user`、`unlock-user` 一律記錄）

## 1. 總則

- 進入點：`python -m app.cli <subcommand> [options]`（`app/cli/__main__.py` 呼叫 `main(argv: Sequence[str] | None = None) -> int`，以 `sys.exit(main())` 結束）。
- 只使用標準函式庫 `argparse`、`getpass`；跨平台（Windows / macOS / Linux）。
- 信任模型：CLI 需伺服器 shell 權限才能執行，視為系統管理者操作，**不做角色檢查**；但仍套用與 Web 相同的輸入驗證與密碼政策，並記錄安全日誌（`actor=cli`，以及 `os_user` = `getpass.getuser()`，取得失敗記 null；**非權威**，只供追查，Security Review NB-6）。
- 只呼叫 `app/services/account_service.py`，不寫原始 SQL；每個指令的寫入在**單一 `immediate_transaction`** 內完成（ADR-003 第 2.1 節），失敗則全部 rollback。
- 讀取 `.env`（`Settings`），使用同一個 `DATABASE_URL`；資料表不存在時顯示「資料庫尚未初始化，請先執行 python -m alembic upgrade head」並以結束碼 1 結束。
- **禁止**以命令列參數或環境變數傳入密碼（避免留在 shell history 與程序清單）；密碼只能經 `getpass.getpass()` 互動輸入兩次。
- **需要輸入密碼的指令（`create-staff`、`create-student`）在 `sys.stdin.isatty()` 為 False 時拒絕執行**（Security Review N-11）：輸出「此指令需在互動式終端機執行」，結束碼 1。理由：非 TTY 時 `getpass` 會退回明碼讀取並發出警告，且常代表密碼被寫在腳本或管線中。不需密碼的指令（`create-club`、`unlock-user`）不受此限。測試以 monkeypatch `sys.stdin.isatty` 與 `getpass.getpass` 模擬。
- 輸出：成功訊息寫 stdout；錯誤訊息寫 stderr，只輸出可理解的中文說明，不輸出 stack trace、SQL 或密碼。
- **重複資料的競態**：service 先查詢唯一性以提供友善訊息，但寫入時仍可能因併發觸發 UNIQUE constraint；CLI 捕捉 `sqlalchemy.exc.IntegrityError` → 顯示「帳號已存在」或「社團名稱已存在」（依指令），結束碼 1（Code Review #17）。
- 結束碼：

| 碼 | 意義 |
|---|---|
| 0 | 成功 |
| 1 | 驗證失敗、資料重複（含 `IntegrityError`）、非 TTY、資料庫未初始化、`ServiceBusyError` 等可預期錯誤 |
| 2 | 參數錯誤（argparse 預設行為） |
| 130 | 使用者以 Ctrl+C 中斷（`KeyboardInterrupt`），不建立任何資料 |

## 2. 共用驗證規則

| 欄位 | 規則 | 錯誤訊息 |
|---|---|---|
| 帳號 `username` | **只能**經 `app/core/security.py` 的 `normalize_username()`（ADR-005 2.1：strip → lower → `fullmatch([a-z0-9._-]{1,50})`）；回傳 None 即不合法 | 「帳號須為 1～50 字的英數字或 . _ -」 |
| 帳號唯一 | `users.username` 不存在 | 「帳號已存在」 |
| 姓名 `display_name` | 去除前後空白；1～50 字；不可含控制字元 | 「姓名須為 1～50 字」 |
| 密碼 | `app/core/security.py` `validate_password_policy(password: str, username: str) -> list[str]`：長度 8～128（以字元計）；不在常見密碼清單（不分大小寫）；不可等於帳號（不分大小寫）；兩次輸入一致 | 「密碼長度須為 8～128 字元」「此密碼過於常見，請改用其他密碼」「密碼不可與帳號相同」「兩次輸入的密碼不一致」 |
| 社團名稱 | 去除前後空白；1～50 字；唯一 | 「社團名稱須為 1～50 字」「社團名稱已存在」 |

密碼不符政策時**重新提示**（最多 3 次），3 次皆失敗則結束碼 1。

## 3. 子指令

### 3.1 `create-staff`（US-013 AC9）

```text
python -m app.cli create-staff [--username USERNAME] [--display-name NAME]
```

- 未提供的參數以 `input()` 互動詢問；密碼一律 `getpass` 輸入兩次。
- 建立 `role='staff'`、`is_active=true` 的帳號，密碼以 `PasswordService.hash()`（argon2id）雜湊。
- 成功輸出：`已建立承辦人帳號：<username>（id=<id>）`。記錄 `account.created`（`role=staff`）。

### 3.2 `create-club`

```text
python -m app.cli create-club --name NAME
```

- 建立 `is_active=true` 的社團。（社團代碼 `--code` 隨 US-014 再加入。）
- 成功輸出：`已建立社團：<name>（id=<id>）`。記錄 `club.created`。

### 3.3 `create-student`

```text
python -m app.cli create-student [--username USERNAME] [--display-name NAME] [--club CLUB_NAME ...]
```

- `--club` 可重複指定（`action='append'`），以**社團名稱**指定負責的社團，可為 0 個；重複名稱自動去重。
- 任一社團不存在 → 「找不到社團：<name>」，**不建立帳號**（整筆 rollback）。
- 建立 `role='student'` 帳號並寫入 `club_managers`。
- 成功輸出：`已建立學生帳號：<username>（id=<id>），負責社團：吉他社、熱舞社`。記錄 `account.created`（`role=student`、`club_ids`）。

### 3.4 `unlock-user`（Security Review N-3）

```text
python -m app.cli unlock-user --username USERNAME
```

- 以 `normalize_username()` 正規化（不合法 → 結束碼 1），刪除 `login_throttles` 中該鍵的列，立即解除鎖定並歸零嘗試數。
- 不檢查帳號是否存在（throttle 列本來就可能屬於不存在的帳號）；沒有該列時輸出「此帳號目前沒有鎖定或失敗紀錄」，結束碼仍為 0。
- 成功輸出：`已解除鎖定：<username>`。**不論是否有該列都記錄** `account.unlocked`（`was_locked` = 刪除前存在該列且 `locked_until > now`，否則 false；Security Review NB-6）。
- 承辦人用的 Web 解鎖介面另立 Backlog 項目（overview.md 第 11 節 #8）。

## 4. Service 介面（T-009 `app/services/account_service.py`）

```python
class AccountService:
    def __init__(self, session: Session, passwords: PasswordService, clock: Clock) -> None: ...
    def create_staff(self, username: str, display_name: str, password: str) -> User: ...
    def create_student(self, username: str, display_name: str, password: str, club_names: Sequence[str]) -> User: ...
    def create_club(self, name: str) -> Club: ...
    def unlock_user(self, username: str) -> bool: ...   # 回傳刪除前是否處於鎖定
    # 驗證失敗拋 FieldErrors（鍵：username / display_name / password / name / club）
```

- 密碼以 `str` 參數直接傳入，不放進 Pydantic model（overview.md 第 5 節）。
- Web 的 US-014 日後重用同一 service，屆時加上 `actor: CurrentUser` 參數與 staff 權限檢查。

## 5. Demo 資料建立步驟（供 T-009 回報、Scrum Master 寫入 demo-script.md）

```bash
python -m alembic upgrade head
python -m app.cli create-staff --username staff01 --display-name 課外組承辦人
python -m app.cli create-club --name 吉他社
python -m app.cli create-club --name 熱舞社
python -m app.cli create-student --username 412345678 --display-name 王小明 --club 吉他社
python -m app.cli create-student --username 412345679 --display-name 李小華 --club 熱舞社
```

（`create-staff`、`create-student` 須在互動式終端機執行，並輸入密碼兩次。）
