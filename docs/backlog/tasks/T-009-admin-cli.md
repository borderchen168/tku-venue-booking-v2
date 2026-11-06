---
id: T-009
title: 管理指令 CLI（建立承辦人、社團、學生）
story: [US-013, US-004]
status: todo        # todo / in-progress / review / done / blocked
assignee: backend-developer
branch: feature/T-009-admin-cli
sprint: sprint-01
depends_on: [T-008]
created: 2026-11-06
---

# T-009 管理指令 CLI（建立承辦人、社團、學生）

## 說明
依 `docs/architecture/cli.md`（第 3 版）提供管理指令：建立第一個承辦人帳號（US-013 AC9）、Sprint 1 Demo 所需的社團與學生（社團負責人）資料（US-014 維護介面尚未實作），
以及解除登入鎖定的 `unlock-user`（ADR-005 第 4 節）。同時建立 T-019、T-020 會使用的 `club_repository`。

## 完成條件
- [ ] `app/cli/__init__.py`、`app/cli/__main__.py`：`main(argv) -> int`、argparse 子指令 `create-staff`、`create-club`、`create-student`、`unlock-user`，參數與輸出訊息依 cli.md 第 3 節；各指令提供 `--help`。
- [ ] `create-club` 只有 `--name`（**不提供 `--code`**，社團代碼隨 US-014 加入）。
- [ ] `unlock-user --username`：以 `normalize_username()` 正規化（不合法 → 結束碼 1）後刪除該鍵的 `login_throttles` 列；無資料列時仍結束碼 0 並顯示「此帳號目前沒有鎖定或失敗紀錄」；**不論是否有該列都記錄** `account.unlocked`（`was_locked` = 刪除前存在該列且 `locked_until > now`，否則 false），cli.md 3.4。
- [ ] **需要輸入密碼的指令（`create-staff`、`create-student`）在 `sys.stdin.isatty()` 為 False 時拒絕執行**，結束碼 1（cli.md 第 1 節）；密碼只經 `getpass` 輸入兩次，不接受命令列參數或環境變數。
- [ ] 驗證規則依 cli.md 第 2 節：**帳號一律經 T-008 `app/core/security.py` 的 `normalize_username()`**（回傳 None 即不合法；不得另寫 `.lower()` 或 regex，ADR-005 2.1）、姓名、`validate_password_policy`、社團名稱；密碼不符政策重新提示最多 3 次。
- [ ] 捕捉 `sqlalchemy.exc.IntegrityError`（併發造成的唯一性衝突）→ 顯示「帳號已存在」或「社團名稱已存在」、結束碼 1；結束碼表依 cli.md 第 1 節（0 / 1 / 2 / 130）。
- [ ] `app/services/account_service.py` `AccountService`（`create_staff`、`create_student`、`create_club`、`unlock_user`）依 cli.md 第 4 節；驗證失敗拋 `FieldErrors`（可用 T-003 的 `to_field_errors`）；每個指令的寫入在**單一 `immediate_transaction`** 內完成（ADR-003 2.1）。
- [ ] `app/repositories/club_repository.py`：`get_by_name`、`add`、`list_managed_by(user_id)`、`is_manager(user_id, club_id)`（overview.md 3.2；後兩者供 T-019、T-020 使用）。
- [ ] 安全日誌：`account.created`、`club.created`、`account.unlocked`（security-logging.md 第 2 節，`actor=cli`，**`os_user` = `getpass.getuser()`，取得失敗記 null**，不含密碼）；`os_user` 非權威，只供追查（cli.md 第 1 節）。
- [ ] CLI 只呼叫 service，不寫原始 SQL；錯誤訊息寫 stderr，不輸出 stack trace 或密碼；資料表不存在時提示先執行 `alembic upgrade head`。
- [ ] 完成回報附上 cli.md 第 5 節 Demo 資料建立步驟的實測結果，由 Scrum Master 寫入 `docs/sprints/sprint-01/demo-script.md`。
- [ ] 測試（monkeypatch `sys.stdin.isatty` 與 `getpass.getpass`）：四個指令的成功與失敗路徑、弱密碼 / 常見密碼 / 與帳號相同被拒、重複帳號被拒、非 TTY 拒絕、`IntegrityError` 轉友善訊息、`create-student` 社團不存在時整筆 rollback、`unlock-user` 有列（鎖定中 / 未鎖定）與無列皆記錄 `account.unlocked` 且 `was_locked` 正確、`unlock-user` 不合法帳號結束碼 1、帳號大小寫與前後空白經正規化（例如 `' Staff01 '` 建立為 `staff01`）、日誌含 `os_user`（monkeypatch `getpass.getuser` 拋例外時為 null）、Ctrl+C 結束碼 130、`club_repository.is_manager` / `list_managed_by`。

## 技術備註
- 信任模型：CLI 不做角色檢查，但套用與 Web 相同的輸入驗證與密碼政策（cli.md 第 1 節）。
- 只使用標準函式庫 `argparse`、`getpass`，跨平台可執行。
- 承辦人用的 Web 解鎖介面不在本 Task（overview.md 第 11 節 #8，待 PO 建立 Backlog）。

## 審查紀錄
| 日期 | 角色 | 結論 | 備註 |
|---|---|---|---|

## DoD(完成定義)
- [ ] ruff check / ruff format --check / mypy 通過
- [ ] pytest 通過，branch coverage ≥ 80%
- [ ] Code Review 通過
- [ ] Security Review 通過
- [ ] QA 驗收通過
- [ ] 文件與 .env.example 已更新
