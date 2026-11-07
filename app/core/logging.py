"""日誌設定與安全日誌 helper（security-logging.md 第 1、2 節）。

- 一般程式日誌：logger `app`。
- 安全事件：logger `security`，每筆為單行 JSON，只能透過 `security_log` 輸出。
- 自動附加欄位所需的 `contextvars` 定義於本模組；HTTP 請求由 T-023 的 `RequestIdMiddleware`
  以 `bind_request_context` 設定，CLI 由 `bind_cli_context` 設定；未設定時輸出 `null`。
"""

import datetime as dt
import json
import logging
import sys
import unicodedata
import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Literal, override

from app.core.config import Settings

APP_LOGGER_NAME: Final = 'app'
SECURITY_LOGGER_NAME: Final = 'security'

USERNAME_MAX_LOG_LENGTH: Final = 50

SECURITY_LOG_FIELDS: Final[frozenset[str]] = frozenset(
    {
        'user_id',
        'actor_id',
        'actor',
        'os_user',
        'username',
        'username_invalid',
        'role',
        'reason',
        'resource',
        'resource_id',
        'concealed',
        'locked_until',
        'attempt_count',
        'was_locked',
        'rejected_count',
        'closed_period_id',
        'start_date',
        'end_date',
        'reason_type',
        'affected_count',
        'booking_id',
        'club_id',
        'club_ids',
        'venue_id',
        'start_at',
        'end_at',
        'status',
    }
)
"""`security_log` 接受的欄位白名單；新增欄位需經 Security Reviewer 同意並更新 security-logging.md 第 2 節。"""

request_id_var: ContextVar[str | None] = ContextVar('request_id', default=None)
client_ip_var: ContextVar[str | None] = ContextVar('client_ip', default=None)
method_var: ContextVar[str | None] = ContextVar('method', default=None)
path_var: ContextVar[str | None] = ContextVar('path', default=None)

# 需要跳脫的 Unicode 類別：Cc（控制字元）、Cf（格式字元，含 U+202E 等 bidi 控制、U+200E/U+200F）、
# Cs（落單的 surrogate，無法正常編碼）、Zl（U+2028）、Zp（U+2029）。
# 這些字元可能被日誌檢視工具視為換行或改變顯示順序（Log Injection，CWE-117）。
_ESCAPED_CATEGORIES: Final = frozenset({'Cc', 'Cf', 'Cs', 'Zl', 'Zp'})

# 反斜線本身也要跳脫，讓原文的 `\\n`（兩個字元）與換行跳脫後的結果可以區分
_APP_SHORT_ESCAPES: Final = {'\\': '\\\\', '\n': '\\n', '\r': '\\r', '\t': '\\t'}

_HANDLER_NAME_PREFIX: Final = 'tku-'

security_logger: Final = logging.getLogger(SECURITY_LOGGER_NAME)


class SecurityEvent(StrEnum):
    """安全事件名稱（security-logging.md 第 2 節）。"""

    AUTH_LOGIN_SUCCESS = 'auth.login.success'
    AUTH_LOGIN_FAILURE = 'auth.login.failure'
    AUTH_LOGIN_LOCKED = 'auth.login.locked'
    AUTH_LOGIN_BUSY = 'auth.login.busy'
    AUTH_LOGOUT = 'auth.logout'
    AUTH_SESSION_EXPIRED = 'auth.session.expired'
    ACCESS_DENIED = 'access.denied'
    CSRF_FAILED = 'csrf.failed'
    CLOSED_PERIOD_CREATED = 'closed_period.created'
    CLOSED_PERIOD_UPDATED = 'closed_period.updated'
    CLOSED_PERIOD_DELETED = 'closed_period.deleted'
    BOOKING_CREATED = 'booking.created'
    ACCOUNT_CREATED = 'account.created'
    CLUB_CREATED = 'club.created'
    ACCOUNT_UNLOCKED = 'account.unlocked'


@dataclass(frozen=True, slots=True)
class RequestContextTokens:
    """`bind_request_context` 回傳的還原憑證，供 `reset_request_context` 使用。"""

    request_id: Token[str | None]
    client_ip: Token[str | None]
    method: Token[str | None]
    path: Token[str | None]


def bind_request_context(*, request_id: str, client_ip: str | None, method: str, path: str) -> RequestContextTokens:
    """設定目前請求的自動附加欄位（由 T-023 `RequestIdMiddleware` 呼叫）。

    `path` 必須是不含查詢字串的路徑。請求結束時以 `reset_request_context` 還原。
    """
    return RequestContextTokens(
        request_id=request_id_var.set(request_id),
        client_ip=client_ip_var.set(client_ip),
        method=method_var.set(method),
        path=path_var.set(path),
    )


def reset_request_context(tokens: RequestContextTokens) -> None:
    """還原 `bind_request_context` 之前的值。"""
    path_var.reset(tokens.path)
    method_var.reset(tokens.method)
    client_ip_var.reset(tokens.client_ip)
    request_id_var.reset(tokens.request_id)


def bind_cli_context() -> str:
    """CLI 執行時呼叫：`request_id` 設為 `cli-<uuid>`，`client_ip`、`method`、`path` 設為 None；回傳 request_id。"""
    request_id = f'cli-{uuid.uuid4()}'
    request_id_var.set(request_id)
    client_ip_var.set(None)
    method_var.set(None)
    path_var.set(None)
    return request_id


def _needs_escape(char: str) -> bool:
    return unicodedata.category(char) in _ESCAPED_CATEGORIES


def _json_unicode_escape(char: str) -> str:
    """JSON 的 `\\uXXXX` 跳脫；BMP 以外的字元以 surrogate pair 表示。"""
    code = ord(char)
    if code <= 0xFFFF:
        return f'\\u{code:04x}'
    code -= 0x10000
    return f'\\u{0xD800 + (code >> 10):04x}\\u{0xDC00 + (code & 0x3FF):04x}'


def _escape_json_line(text: str) -> str:
    """補跳脫 `json.dumps(ensure_ascii=False)` 未處理的 Cc / Cf / Cs / Zl / Zp 字元，結果仍是合法的單行 JSON。"""
    if text.isascii() and text.isprintable():
        return text
    return ''.join(_json_unicode_escape(char) if _needs_escape(char) else char for char in text)


def escape_log_text(text: str) -> str:
    """一般日誌訊息的跳脫：反斜線改為 `\\\\`；CR / LF / TAB 改為 `\\r` / `\\n` / `\\t`；其他 Cc / Cf / Cs / Zl / Zp 改為 `\\uXXXX`。"""
    if text.isascii() and text.isprintable() and '\\' not in text:
        return text
    parts: list[str] = []
    for char in text:
        if char in _APP_SHORT_ESCAPES:
            parts.append(_APP_SHORT_ESCAPES[char])
        elif _needs_escape(char):
            code = ord(char)
            parts.append(f'\\u{code:04x}' if code <= 0xFFFF else f'\\U{code:08x}')
        else:
            parts.append(char)
    return ''.join(parts)


class EscapingFormatter(logging.Formatter):
    """跳脫 `%(message)s` 中的換行與控制字元，確保每筆訊息只占一行（`app` logger 使用）。

    例外的 traceback（`exc_info`）仍以多行附加在後，只寫入伺服器日誌。
    """

    @override
    def formatMessage(self, record: logging.LogRecord) -> str:
        """以跳脫後的訊息套用格式，結束後還原 `record.message`，避免影響其他 handler。"""
        original = record.message
        record.message = escape_log_text(original)
        try:
            return super().formatMessage(record)
        finally:
            record.message = original


def security_log(
    event: SecurityEvent,
    *,
    outcome: Literal['success', 'failure'] = 'success',
    **fields: str | int | bool | None,
) -> None:
    """記錄安全事件；fields 只接受 `SECURITY_LOG_FIELDS` 白名單欄位，其他鍵名直接拋 ValueError（開發期即發現誤記錄）。

    輸出為單行 JSON（字串值經 JSON 序列化；換行、控制字元、bidi 等格式字元與 U+2028 / U+2029 皆被跳脫）；`username` 截斷至 50 字。
    `outcome='failure'` 以 WARNING 等級記錄，其餘為 INFO。

    Raises:
        ValueError: 欄位名稱不在 `SECURITY_LOG_FIELDS`，或 `outcome` 不合法。
        TypeError: 欄位值不是 `str`、`int`、`bool` 或 `None`。
    """
    unknown = sorted(set(fields) - SECURITY_LOG_FIELDS)
    if unknown:
        raise ValueError(f'security_log 不接受的欄位：{", ".join(unknown)}')
    if outcome not in ('success', 'failure'):
        raise ValueError('security_log 的 outcome 只能是 success 或 failure')
    event = SecurityEvent(event)

    record: dict[str, str | int | bool | None] = {
        'ts': dt.datetime.now(dt.UTC).isoformat(),
        'event': event.value,
        'outcome': outcome,
        'request_id': request_id_var.get(),
        'client_ip': client_ip_var.get(),
        'method': method_var.get(),
        'path': path_var.get(),
    }
    for key, value in fields.items():
        if value is not None and not isinstance(value, str | int):  # bool 為 int 子類別
            raise TypeError(f'security_log 欄位 {key} 的型別不支援')
        if key == 'username' and isinstance(value, str):
            value = value[:USERNAME_MAX_LOG_LENGTH]
        record[key] = value

    line = _escape_json_line(json.dumps(record, ensure_ascii=False))
    security_logger.log(logging.WARNING if outcome == 'failure' else logging.INFO, line)


def configure_logging(settings: Settings) -> None:
    """設定 `app` 與 `security` logger：輸出到 stderr、等級為 `LOG_LEVEL`。可重複呼叫，不會重複加入 handler。

    `security` 只輸出訊息本身（已是跳脫過的 JSON）；`app` 使用 `EscapingFormatter` 跳脫訊息中的換行與控制字元。
    兩者保持 propagate，以便 pytest `caplog` 擷取；root logger 預設沒有 handler，正式執行時不會重複輸出。

    **呼叫時機**：`create_app` 會呼叫；CLI（T-009）等不經 `create_app` 的進入點，必須在記錄任何日誌（含
    `bind_cli_context` 後的 `security_log`）之前先呼叫本函式，否則安全事件不會輸出到 stderr。
    """
    formatters: dict[str, logging.Formatter] = {
        APP_LOGGER_NAME: EscapingFormatter('%(asctime)s %(levelname)s %(name)s %(message)s'),
        SECURITY_LOGGER_NAME: logging.Formatter('%(message)s'),
    }
    for name, formatter in formatters.items():
        logger = logging.getLogger(name)
        logger.setLevel(settings.LOG_LEVEL)
        handler_name = _HANDLER_NAME_PREFIX + name
        if any(handler.get_name() == handler_name for handler in logger.handlers):
            continue
        handler = logging.StreamHandler(sys.stderr)
        handler.set_name(handler_name)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
