"""Domain 例外與 HTTP 層流程控制例外（error-handling.md 第 2 節）。

service 只拋 domain 例外、不知道 HTTP；轉換為回應由 route 或全域 exception handler（T-023）負責。
"""

from typing import Literal

CSRFReason = Literal['missing', 'mismatch', 'no_session', 'no_nonce', 'expired', 'bad_format']
"""`CSRFError.reason` 的合法值；與 security-logging.md `csrf.failed` 的 `reason` 一致。"""


class DomainError(Exception):
    """所有 domain 例外的基底；message 為可直接顯示給使用者的繁體中文。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """資源不存在 → 404（不記錄 access.denied）。"""


class PermissionDeniedError(DomainError):
    """→ 403；conceal=True 時改以 404 呈現（隱藏資源存在與否）。access.denied 一律由全域 handler 記錄。"""

    def __init__(
        self,
        message: str = '您沒有權限執行此操作',
        *,
        reason: str,
        resource: str | None = None,
        resource_id: int | None = None,
        conceal: bool = False,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.resource = resource
        self.resource_id = resource_id
        self.conceal = conceal


class FieldErrors(DomainError):
    """表單逐欄錯誤 → 422；也用於查詢參數驗證（週檢視）。

    `errors` 為「欄位名 → 訊息」，鍵 `__all__` 代表全域錯誤。
    """

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__(errors.get('__all__', '輸入資料有誤，請修正後再送出'))
        self.errors = dict(errors)


class BusinessRuleError(DomainError):
    """商業規則不符 → 表單 422（頂部訊息）；`code` 供測試斷言（白名單見 error-handling.md 第 2 節）。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class BookingConflictError(DomainError):
    """預約時段重疊 → 表單 409「該時段已被借用」。"""


class ServiceBusyError(DomainError):
    """系統忙碌（SQLite 寫鎖逾時、雜湊名額已滿）→ 503「系統忙碌，請稍後再試」＋ Retry-After。"""


class CSRFError(Exception):
    """CSRF 驗證失敗 → 403 CSRF 錯誤頁 + csrf.failed。

    no_session：/logout 時沒有有效已登入 Session；no_nonce：未登入且沒有（或格式不合的）登入前 nonce Cookie。
    """

    def __init__(self, *, reason: CSRFReason) -> None:
        super().__init__(reason)
        self.reason: CSRFReason = reason


class LoginRequired(Exception):
    """需要登入 → 303 /login（`next_path` 為站內相對路徑或 None；`timed_out` 時加 reason=timeout）。"""

    def __init__(self, next_path: str | None, timed_out: bool) -> None:
        super().__init__('login required')
        self.next_path = next_path
        self.timed_out = timed_out
