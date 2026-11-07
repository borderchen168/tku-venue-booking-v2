"""security_log / configure_logging 測試（security-logging.md 第 1、2 節）。"""

import json
import logging
import sys
import uuid
from collections.abc import Iterator
from contextvars import ContextVar
from pathlib import Path

import pytest

from app.core import logging as app_logging
from app.core.logging import (
    SECURITY_LOG_FIELDS,
    SECURITY_LOGGER_NAME,
    EscapingFormatter,
    SecurityEvent,
    bind_cli_context,
    bind_request_context,
    configure_logging,
    escape_log_text,
    reset_request_context,
    security_log,
)
from tests.fixtures.settings import make_settings

# U+2028 LINE SEPARATOR、U+2029 PARAGRAPH SEPARATOR（部分檢視工具視為換行）
LINE_SEPARATORS = chr(0x2028) + chr(0x2029)
# bidi 與格式字元（Cf）：U+202E RLO、U+2066～U+2069 isolate、U+200E LRM、U+200F RLM、U+E0001 LANGUAGE TAG
BIDI_CHARS = ''.join(chr(code) for code in (0x202E, 0x2066, 0x2067, 0x2068, 0x2069, 0x200E, 0x200F, 0xE0001))
# Cc：C0、DEL、C1
CONTROL_CHARS = '\x00\x1b\x7f\x85\x9b'

CONTEXT_VARS: tuple[ContextVar[str | None], ...] = (
    app_logging.request_id_var,
    app_logging.client_ip_var,
    app_logging.method_var,
    app_logging.path_var,
)

EXPECTED_EVENTS = {
    'auth.login.success',
    'auth.login.failure',
    'auth.login.locked',
    'auth.login.busy',
    'auth.logout',
    'auth.session.expired',
    'access.denied',
    'csrf.failed',
    'closed_period.created',
    'closed_period.updated',
    'closed_period.deleted',
    'booking.created',
    'account.created',
    'club.created',
    'account.unlocked',
}


@pytest.fixture(autouse=True)
def clean_context() -> Iterator[None]:
    """每個測試前後清空 contextvars，避免互相影響。"""
    tokens = [(var, var.set(None)) for var in CONTEXT_VARS]
    yield
    for var, token in reversed(tokens):
        var.reset(token)


def security_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.name == SECURITY_LOGGER_NAME]


def last_entry(caplog: pytest.LogCaptureFixture) -> dict[str, object]:
    records = security_records(caplog)
    assert records, '沒有 security 日誌'
    message = records[-1].getMessage()
    assert '\n' not in message
    assert '\r' not in message
    parsed = json.loads(message)
    assert isinstance(parsed, dict)
    return parsed


def test_security_event_values_match_spec() -> None:
    assert {event.value for event in SecurityEvent} == EXPECTED_EVENTS


def test_whitelist_matches_spec() -> None:
    assert 'os_user' in SECURITY_LOG_FIELDS
    assert 'rejected_count' in SECURITY_LOG_FIELDS
    assert len(SECURITY_LOG_FIELDS) == 27


def test_outputs_single_line_json_with_auto_fields(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=SECURITY_LOGGER_NAME)
    security_log(SecurityEvent.AUTH_LOGIN_SUCCESS, user_id=1, username='s123', role='student')
    entry = last_entry(caplog)
    assert entry['event'] == 'auth.login.success'
    assert entry['outcome'] == 'success'
    assert entry['user_id'] == 1
    assert entry['role'] == 'student'
    for key in ('ts', 'request_id', 'client_ip', 'method', 'path'):
        assert key in entry
    assert entry['request_id'] is None
    assert entry['client_ip'] is None
    assert isinstance(entry['ts'], str)
    assert entry['ts'].endswith('+00:00')
    assert security_records(caplog)[-1].levelno == logging.INFO


def test_failure_logged_as_warning(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=SECURITY_LOGGER_NAME)
    security_log(SecurityEvent.CSRF_FAILED, outcome='failure', user_id=None, reason='missing')
    entry = last_entry(caplog)
    assert entry['outcome'] == 'failure'
    assert entry['user_id'] is None
    assert security_records(caplog)[-1].levelno == logging.WARNING


@pytest.mark.parametrize('key', ['password', 'csrf_token', 'display_name', 'session_id', 'ts', 'outcome_detail', 'request_id', 'path'])
def test_rejects_non_whitelisted_key(caplog: pytest.LogCaptureFixture, key: str) -> None:
    caplog.set_level(logging.INFO, logger=SECURITY_LOGGER_NAME)
    with pytest.raises(ValueError, match=key):
        security_log(SecurityEvent.AUTH_LOGIN_FAILURE, outcome='failure', **{key: 'secret-value'})
    assert not security_records(caplog)


def test_rejects_unsupported_value_type() -> None:
    with pytest.raises(TypeError):
        security_log(SecurityEvent.BOOKING_CREATED, start_at=object())


def test_rejects_invalid_outcome() -> None:
    with pytest.raises(ValueError, match='outcome'):
        security_log(SecurityEvent.AUTH_LOGOUT, outcome='maybe')


def test_rejects_unknown_event_string() -> None:
    with pytest.raises(ValueError, match=r'not\.an\.event'):
        security_log('not.an.event')


def test_control_characters_are_escaped(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=SECURITY_LOGGER_NAME)
    injected = 'evil\n{"event":"auth.login.success"}\r\x1b[31m\x00\x7f\x85' + LINE_SEPARATORS
    security_log(SecurityEvent.AUTH_LOGIN_FAILURE, outcome='failure', username=injected, reason='unknown_user')
    message = security_records(caplog)[-1].getMessage()
    for raw in ('\n', '\r', '\x1b', '\x00', '\x7f', '\x85', *LINE_SEPARATORS):
        assert raw not in message
    assert len(message.splitlines()) == 1
    entry = json.loads(message)
    assert entry['username'] == injected[:50]
    assert entry['event'] == 'auth.login.failure'


def test_username_truncated_to_50(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=SECURITY_LOGGER_NAME)
    security_log(SecurityEvent.AUTH_LOGIN_FAILURE, outcome='failure', username='u' * 80, reason='invalid_format')
    assert last_entry(caplog)['username'] == 'u' * 50


def test_username_none_and_invalid_flag(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=SECURITY_LOGGER_NAME)
    security_log(SecurityEvent.AUTH_LOGIN_FAILURE, outcome='failure', username=None, username_invalid=True, reason='invalid_format')
    entry = last_entry(caplog)
    assert entry['username'] is None
    assert entry['username_invalid'] is True


def test_non_ascii_output_kept_readable(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=SECURITY_LOGGER_NAME)
    security_log(SecurityEvent.ACCESS_DENIED, outcome='failure', reason='不是負責人')
    assert '不是負責人' in security_records(caplog)[-1].getMessage()


def test_login_busy_with_rejected_count(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=SECURITY_LOGGER_NAME)
    security_log(SecurityEvent.AUTH_LOGIN_BUSY, outcome='failure', rejected_count=12)
    entry = last_entry(caplog)
    assert entry['event'] == 'auth.login.busy'
    assert entry['rejected_count'] == 12
    assert 'username' not in entry


def test_request_context_fields(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=SECURITY_LOGGER_NAME)
    tokens = bind_request_context(request_id='abc123', client_ip='203.0.113.5', method='POST', path='/login')
    try:
        security_log(SecurityEvent.AUTH_LOGOUT, user_id=3)
    finally:
        reset_request_context(tokens)
    entry = last_entry(caplog)
    assert entry['request_id'] == 'abc123'
    assert entry['client_ip'] == '203.0.113.5'
    assert entry['method'] == 'POST'
    assert entry['path'] == '/login'

    security_log(SecurityEvent.AUTH_LOGOUT, user_id=3)
    assert last_entry(caplog)['request_id'] is None


def test_cli_context(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=SECURITY_LOGGER_NAME)
    request_id = bind_cli_context()
    assert request_id.startswith('cli-')
    uuid.UUID(request_id.removeprefix('cli-'))
    security_log(SecurityEvent.CLUB_CREATED, actor='cli', os_user='admin', club_id=1)
    entry = last_entry(caplog)
    assert entry['request_id'] == request_id
    assert entry['client_ip'] is None
    assert entry['actor'] == 'cli'
    assert entry['os_user'] == 'admin'


def test_configure_logging_is_idempotent(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, LOG_LEVEL='WARNING')
    configure_logging(settings)
    configure_logging(settings)
    for name in ('app', 'security'):
        logger = logging.getLogger(name)
        assert logger.level == logging.WARNING
        assert len([h for h in logger.handlers if (h.get_name() or '').startswith('tku-')]) == 1
        assert logger.propagate is True


def test_bidi_and_format_characters_are_escaped(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=SECURITY_LOGGER_NAME)
    injected = 'adm' + BIDI_CHARS + CONTROL_CHARS + 'in'
    security_log(SecurityEvent.AUTH_LOGIN_FAILURE, outcome='failure', username=injected, reason='unknown_user')
    message = security_records(caplog)[-1].getMessage()
    for char in BIDI_CHARS + CONTROL_CHARS:
        assert char not in message
    assert '\\u202e' in message
    assert '\\udb40\\udc01' in message  # BMP 以外的字元以 surrogate pair 跳脫
    assert json.loads(message)['username'] == injected[:50]


def test_escape_log_text() -> None:
    raw = 'line1\nline2\r\tend' + BIDI_CHARS + CONTROL_CHARS + LINE_SEPARATORS + '中文 ok'
    escaped = escape_log_text(raw)
    assert escaped.startswith('line1\\nline2\\r\\tend\\u202e')
    assert '\\U000e0001' in escaped
    assert '\\u2028\\u2029' in escaped
    assert escaped.endswith('中文 ok')
    for char in '\n\r\t' + BIDI_CHARS + CONTROL_CHARS + LINE_SEPARATORS:
        assert char not in escaped
    assert escape_log_text('plain ascii') == 'plain ascii'


def test_escaping_formatter_keeps_single_line_and_restores_record() -> None:
    formatter = EscapingFormatter('%(levelname)s %(message)s')
    record = logging.LogRecord('app', logging.WARNING, __file__, 1, 'user %s', ('x\nFAKE INFO admin login' + BIDI_CHARS,), None)
    output = formatter.format(record)
    assert output.startswith('WARNING user x\\nFAKE INFO admin login\\u202e')
    assert '\n' not in output
    assert '\n' in record.message  # 其他 handler（例如 caplog）看到的原始訊息不受影響


def test_escaping_formatter_keeps_traceback() -> None:
    formatter = EscapingFormatter('%(message)s')
    try:
        raise RuntimeError('boom')
    except RuntimeError:
        record = logging.LogRecord('app', logging.ERROR, __file__, 1, 'failed\nforged', None, sys.exc_info())
    output = formatter.format(record)
    first_line, _, rest = output.partition('\n')
    assert first_line == 'failed\\nforged'
    assert 'Traceback' in rest


def test_configure_logging_uses_escaping_formatter_for_app(tmp_path: Path) -> None:
    configure_logging(make_settings(tmp_path))
    app_handlers = [h for h in logging.getLogger('app').handlers if h.get_name() == 'tku-app']
    security_handlers = [h for h in logging.getLogger('security').handlers if h.get_name() == 'tku-security']
    assert isinstance(app_handlers[0].formatter, EscapingFormatter)
    assert not isinstance(security_handlers[0].formatter, EscapingFormatter)


def test_app_logger_output_is_single_line(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(make_settings(tmp_path))
    handler = next(h for h in logging.getLogger('app').handlers if h.get_name() == 'tku-app')
    assert isinstance(handler, logging.StreamHandler)
    original_stream = handler.setStream(sys.stderr)  # 暫時指向 capsys 替換後的 stderr
    try:
        logging.getLogger('app').warning('bad input %s', 'a\r\nb' + LINE_SEPARATORS)
    finally:
        if original_stream is not None:
            handler.setStream(original_stream)
    lines = [line for line in capsys.readouterr().err.splitlines() if 'bad input' in line]
    assert len(lines) == 1
    assert lines[0].endswith('bad input a\\r\\nb\\u2028\\u2029')


def test_escape_log_text_escapes_backslash() -> None:
    literal = 'path\\nname'  # 原文是反斜線 + n，不是換行
    newline = 'path\nname'
    assert escape_log_text(literal) == 'path\\\\nname'
    assert escape_log_text(newline) == 'path\\nname'
    assert escape_log_text(literal) != escape_log_text(newline)
    assert escape_log_text('C:\\temp') == 'C:\\\\temp'


def test_lone_surrogate_is_escaped(caplog: pytest.LogCaptureFixture) -> None:
    lone = chr(0xD800)
    assert escape_log_text('x' + lone + 'y') == 'x\\ud800y'
    caplog.set_level(logging.INFO, logger=SECURITY_LOGGER_NAME)
    security_log(SecurityEvent.AUTH_LOGIN_FAILURE, outcome='failure', username='u' + lone, reason='unknown_user')
    message = security_records(caplog)[-1].getMessage()
    assert lone not in message
    message.encode('utf-8')  # 不再含無法編碼的字元
    assert json.loads(message)['username'] == 'u' + lone
