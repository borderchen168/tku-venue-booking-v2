"""例外類別測試（error-handling.md 第 2 節）。"""

import pytest

from app.core.exceptions import (
    BookingConflictError,
    BusinessRuleError,
    CSRFError,
    DomainError,
    FieldErrors,
    LoginRequired,
    NotFoundError,
    PermissionDeniedError,
    ServiceBusyError,
)


def test_domain_error_message() -> None:
    exc = DomainError('發生錯誤')
    assert exc.message == '發生錯誤'
    assert str(exc) == '發生錯誤'


@pytest.mark.parametrize(
    'cls',
    [NotFoundError, PermissionDeniedError, FieldErrors, BusinessRuleError, BookingConflictError, ServiceBusyError],
)
def test_domain_subclasses(cls: type[Exception]) -> None:
    assert issubclass(cls, DomainError)


def test_http_flow_exceptions_are_not_domain_errors() -> None:
    assert not issubclass(CSRFError, DomainError)
    assert not issubclass(LoginRequired, DomainError)


def test_simple_domain_errors_keep_message() -> None:
    assert NotFoundError('找不到場地').message == '找不到場地'
    assert BookingConflictError('該時段已被借用').message == '該時段已被借用'
    assert ServiceBusyError('系統忙碌，請稍後再試').message == '系統忙碌，請稍後再試'


def test_permission_denied_defaults() -> None:
    exc = PermissionDeniedError(reason='role_required:staff')
    assert exc.message == '您沒有權限執行此操作'
    assert exc.reason == 'role_required:staff'
    assert exc.resource is None
    assert exc.resource_id is None
    assert exc.conceal is False


def test_permission_denied_conceal() -> None:
    exc = PermissionDeniedError(reason='not_owner', resource='booking_application', resource_id=7, conceal=True)
    assert exc.resource == 'booking_application'
    assert exc.resource_id == 7
    assert exc.conceal is True


def test_permission_denied_reason_is_keyword_only() -> None:
    with pytest.raises(TypeError):
        PermissionDeniedError('訊息', 'not_owner')


def test_field_errors() -> None:
    errors = {'start_date': '開始日期為必填欄位'}
    exc = FieldErrors(errors)
    assert exc.errors == errors
    assert exc.errors is not errors
    assert exc.message


def test_field_errors_global_message() -> None:
    exc = FieldErrors({'__all__': '結束日期不可早於開始日期'})
    assert exc.message == '結束日期不可早於開始日期'


def test_business_rule_error() -> None:
    exc = BusinessRuleError('closed_date', '該日期不開放借用')
    assert exc.code == 'closed_date'
    assert exc.message == '該日期不開放借用'


@pytest.mark.parametrize('reason', ['missing', 'mismatch', 'no_session', 'no_nonce', 'expired', 'bad_format'])
def test_csrf_error_reason(reason: str) -> None:
    exc = CSRFError(reason=reason)
    assert exc.reason == reason


def test_csrf_error_requires_keyword() -> None:
    with pytest.raises(TypeError):
        CSRFError('missing')


def test_login_required() -> None:
    exc = LoginRequired('/bookings/new?venue_id=1', True)
    assert exc.next_path == '/bookings/new?venue_id=1'
    assert exc.timed_out is True
    exc = LoginRequired(None, False)
    assert exc.next_path is None
    assert exc.timed_out is False
