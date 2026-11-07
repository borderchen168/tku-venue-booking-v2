"""Settings 驗證測試（overview.md 第 4 節、ADR-002 4.4 / 4.5）。"""

import secrets
import string
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import FORBIDDEN_SECRET_KEYS, PROJECT_ROOT, Settings, get_settings
from tests.fixtures.settings import make_settings

STRONG_SECRET = string.ascii_letters + string.digits  # 62 字元、62 種不同字元


def production_overrides(**overrides: Any) -> dict[str, Any]:
    """合法的正式環境設定；個別測試再覆寫一項造成失敗。"""
    values: dict[str, Any] = {
        'APP_ENV': 'production',
        'APP_DEBUG': False,
        'SECRET_KEY': STRONG_SECRET,
        'SESSION_COOKIE_NAME': '__Host-tku_session',
        'SESSION_COOKIE_SECURE': True,
        'ALLOWED_HOSTS': ['venue.example.edu.tw'],
    }
    values.update(overrides)
    return values


def read_env_example_value(name: str) -> str:
    """解析 `.env.example` 中指定變數的值。"""
    env_example = PROJECT_ROOT / '.env.example'
    with env_example.open(encoding='utf-8') as file:
        for line in file:
            stripped = line.strip()
            if stripped.startswith(f'{name}='):
                return stripped.split('=', 1)[1]
    raise AssertionError(f'.env.example 沒有 {name}')


# ---------- 預設值與一般欄位 ----------


def test_defaults() -> None:
    settings = Settings(_env_file=None, SECRET_KEY='x')
    assert settings.APP_ENV == 'development'
    assert settings.APP_DEBUG is False
    assert settings.DATABASE_BUSY_TIMEOUT_MS == 5000
    assert settings.APP_TIMEZONE == 'Asia/Taipei'
    assert settings.ALLOWED_HOSTS == ['localhost', '127.0.0.1']
    assert settings.MAX_REQUEST_BODY_BYTES == 65536
    assert settings.SESSION_COOKIE_NAME == 'tku_session'
    assert settings.SESSION_COOKIE_SECURE is False
    assert settings.SESSION_MAX_AGE_SECONDS == 1800
    assert settings.SESSION_ABSOLUTE_MAX_AGE_SECONDS == 28800
    assert settings.LOGIN_CSRF_MAX_AGE_SECONDS == 3600
    assert settings.LOGIN_MAX_ATTEMPTS == 5
    assert settings.LOGIN_LOCKOUT_SECONDS == 900
    assert settings.PASSWORD_HASH_CONCURRENCY == 4
    assert settings.LOG_LEVEL == 'INFO'
    assert 'sqlite:///' + (PROJECT_ROOT / 'data' / 'app.db').resolve().as_posix() == settings.DATABASE_URL
    assert settings.is_production is False


def test_secret_key_is_required() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_secret_key_is_not_exposed_in_repr(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, SECRET_KEY='very-secret-value-0123456789')
    assert 'very-secret-value' not in repr(settings)
    assert 'very-secret-value' not in str(settings)


def test_reads_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('SECRET_KEY', 'from-env')
    monkeypatch.setenv('ALLOWED_HOSTS', ' a.example , b.example ,, ')
    monkeypatch.setenv('LOGIN_MAX_ATTEMPTS', '7')
    settings = Settings(_env_file=None)
    assert settings.SECRET_KEY.get_secret_value() == 'from-env'
    assert settings.ALLOWED_HOSTS == ['a.example', 'b.example']
    assert settings.LOGIN_MAX_ATTEMPTS == 7


def test_reads_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / '.env'
    env_file.write_text('SECRET_KEY=from-file\nAPP_TIMEZONE=UTC\n', encoding='utf-8')
    settings = Settings(_env_file=env_file)
    assert settings.SECRET_KEY.get_secret_value() == 'from-file'
    assert settings.APP_TIMEZONE == 'UTC'


def test_get_settings_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('SECRET_KEY', 'cached')
    assert get_settings() is get_settings()


def test_settings_is_frozen(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    with pytest.raises(ValidationError):
        settings.APP_ENV = 'production'


@pytest.mark.parametrize('value', ['staging', 'PRODUCTION', ''])
def test_app_env_whitelist(tmp_path: Path, value: str) -> None:
    with pytest.raises(ValidationError):
        make_settings(tmp_path, APP_ENV=value)


@pytest.mark.parametrize('value', ['TRACE', 'info', 'CRITICAL'])
def test_log_level_whitelist(tmp_path: Path, value: str) -> None:
    with pytest.raises(ValidationError):
        make_settings(tmp_path, LOG_LEVEL=value)


@pytest.mark.parametrize('value', ['tku session', 'tku;session', 'tku=session', '', 'a' * 65])
def test_session_cookie_name_format(tmp_path: Path, value: str) -> None:
    with pytest.raises(ValidationError):
        make_settings(tmp_path, SESSION_COOKIE_NAME=value)


# ---------- 數值範圍邊界 ----------

RANGE_CASES = [
    ('DATABASE_BUSY_TIMEOUT_MS', 100, 60000),
    ('MAX_REQUEST_BODY_BYTES', 1024, 1048576),
    ('LOGIN_CSRF_MAX_AGE_SECONDS', 300, 86400),
    ('LOGIN_MAX_ATTEMPTS', 1, 100),
    ('PASSWORD_HASH_CONCURRENCY', 1, 32),
]


@pytest.mark.parametrize(('field', 'low', 'high'), RANGE_CASES)
def test_numeric_range_accepts_bounds(tmp_path: Path, field: str, low: int, high: int) -> None:
    assert getattr(make_settings(tmp_path, **{field: low}), field) == low
    assert getattr(make_settings(tmp_path, **{field: high}), field) == high


@pytest.mark.parametrize(('field', 'low', 'high'), RANGE_CASES)
def test_numeric_range_rejects_out_of_bounds(tmp_path: Path, field: str, low: int, high: int) -> None:
    with pytest.raises(ValidationError):
        make_settings(tmp_path, **{field: low - 1})
    with pytest.raises(ValidationError):
        make_settings(tmp_path, **{field: high + 1})


@pytest.mark.parametrize('field', ['SESSION_MAX_AGE_SECONDS', 'SESSION_ABSOLUTE_MAX_AGE_SECONDS', 'LOGIN_LOCKOUT_SECONDS'])
def test_durations_must_be_positive(tmp_path: Path, field: str) -> None:
    with pytest.raises(ValidationError):
        make_settings(tmp_path, **{field: 0})


def test_absolute_max_age_may_equal_idle_max_age(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, SESSION_MAX_AGE_SECONDS=600, SESSION_ABSOLUTE_MAX_AGE_SECONDS=600)
    assert settings.SESSION_ABSOLUTE_MAX_AGE_SECONDS == 600


def test_absolute_max_age_less_than_idle_fails(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match='SESSION_ABSOLUTE_MAX_AGE_SECONDS'):
        make_settings(tmp_path, SESSION_MAX_AGE_SECONDS=601, SESSION_ABSOLUTE_MAX_AGE_SECONDS=600)


# ---------- APP_TIMEZONE ----------


def test_timezone_valid(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, APP_TIMEZONE='Asia/Taipei')
    assert settings.tz.key == 'Asia/Taipei'


@pytest.mark.parametrize('value', ['Mars/Olympus', '../../etc/passwd', '', 'Asia/Taipei\x00'])
def test_timezone_invalid(tmp_path: Path, value: str) -> None:
    with pytest.raises(ValidationError, match='APP_TIMEZONE'):
        make_settings(tmp_path, APP_TIMEZONE=value)


# ---------- DATABASE_URL ----------


def test_database_url_relative_path_resolved_from_project_root(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, DATABASE_URL='sqlite:///./data/dev.db')
    expected = (PROJECT_ROOT / 'data' / 'dev.db').resolve()
    assert settings.database_path == expected
    assert 'sqlite:///' + expected.as_posix() == settings.DATABASE_URL


def test_database_url_absolute_path_kept(tmp_path: Path) -> None:
    db_path = (tmp_path / 'abs.db').resolve()
    settings = make_settings(tmp_path, DATABASE_URL=f'sqlite:///{db_path.as_posix()}')
    assert settings.database_path == db_path


@pytest.mark.parametrize(
    'value',
    [
        'postgresql://user:pass@localhost/db',
        'sqlite://relative.db',
        'sqlite://',
        'sqlite+pysqlite:///./data/app.db',
        'sqlite:///',
        'sqlite:///:memory:',
        'sqlite:///./data/app.db?mode=ro',
        './data/app.db',
    ],
)
def test_database_url_rejects_non_sqlite_file(tmp_path: Path, value: str) -> None:
    with pytest.raises(ValidationError, match='DATABASE_URL'):
        make_settings(tmp_path, DATABASE_URL=value)


# ---------- __Host- Cookie（不論環境） ----------


@pytest.mark.parametrize('app_env', ['development', 'test'])
def test_host_prefix_cookie_requires_secure_in_any_env(tmp_path: Path, app_env: str) -> None:
    with pytest.raises(ValidationError, match='SESSION_COOKIE_SECURE'):
        make_settings(tmp_path, APP_ENV=app_env, SESSION_COOKIE_NAME='__Host-tku_session', SESSION_COOKIE_SECURE=False)


def test_host_prefix_cookie_with_secure_ok_in_development(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, APP_ENV='development', SESSION_COOKIE_NAME='__Host-tku_session', SESSION_COOKIE_SECURE=True)
    assert settings.SESSION_COOKIE_SECURE is True


# ---------- production 啟動條件 ----------


def test_production_valid_settings(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, **production_overrides())
    assert settings.is_production is True


def test_production_rejects_debug(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match='APP_DEBUG'):
        make_settings(tmp_path, **production_overrides(APP_DEBUG=True))


def test_production_rejects_short_secret_key(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match='SECRET_KEY'):
        make_settings(tmp_path, **production_overrides(SECRET_KEY='s' * 31))


def test_production_accepts_secret_key_of_exactly_32(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, **production_overrides(SECRET_KEY=string.ascii_letters[:32]))
    assert len(settings.SECRET_KEY.get_secret_value()) == 32


@pytest.mark.parametrize('secret', sorted(FORBIDDEN_SECRET_KEYS))
def test_production_rejects_forbidden_secret_key(tmp_path: Path, secret: str) -> None:
    with pytest.raises(ValidationError, match='SECRET_KEY'):
        make_settings(tmp_path, **production_overrides(SECRET_KEY=secret))


def test_production_rejects_cookie_name_without_host_prefix(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match='__Host-'):
        make_settings(tmp_path, **production_overrides(SESSION_COOKIE_NAME='tku_session'))


def test_production_rejects_insecure_cookie(tmp_path: Path) -> None:
    # 不使用 __Host- 名稱以隔離「SESSION_COOKIE_SECURE=false」這一項（__Host- 規則另有測試）
    with pytest.raises(ValidationError, match='SESSION_COOKIE_SECURE 必須為 true'):
        make_settings(tmp_path, **production_overrides(SESSION_COOKIE_NAME='tku_session', SESSION_COOKIE_SECURE=False))


@pytest.mark.parametrize('hosts', [[], ['*'], ['venue.example.edu.tw', '*'], ['*.edu'], ['venue.*.edu.tw'], '', ' , '])
def test_production_rejects_empty_or_wildcard_hosts(tmp_path: Path, hosts: object) -> None:
    with pytest.raises(ValidationError, match='ALLOWED_HOSTS'):
        make_settings(tmp_path, **production_overrides(ALLOWED_HOSTS=hosts))


def test_non_production_allows_weak_settings(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, APP_ENV='development', APP_DEBUG=True, SECRET_KEY='change-me', ALLOWED_HOSTS=['*'])
    assert settings.APP_DEBUG is True


def test_validation_error_does_not_leak_secret(tmp_path: Path) -> None:
    secret = 'leaky-secret-value-0123456789-abcdefghij'
    with pytest.raises(ValidationError) as exc_info:
        make_settings(tmp_path, **production_overrides(SECRET_KEY=secret, APP_DEBUG=True))
    assert secret not in str(exc_info.value)
    assert secret[-10:] not in str(exc_info.value)


# ---------- .env.example 同步 ----------


def test_env_example_secret_key_is_forbidden() -> None:
    assert read_env_example_value('SECRET_KEY') in FORBIDDEN_SECRET_KEYS


def test_env_example_lists_all_settings_fields() -> None:
    for name in Settings.model_fields:
        read_env_example_value(name)


def test_env_example_is_valid_for_development(tmp_path: Path) -> None:
    settings = Settings(_env_file=PROJECT_ROOT / '.env.example')
    assert settings.APP_ENV == 'development'


def test_env_example_secret_key_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match='SECRET_KEY'):
        Settings(_env_file=PROJECT_ROOT / '.env.example', **production_overrides(SECRET_KEY=read_env_example_value('SECRET_KEY')))


@pytest.mark.parametrize('value', [None, 123])
def test_allowed_hosts_rejects_non_list(tmp_path: Path, value: object) -> None:
    with pytest.raises(ValidationError):
        make_settings(tmp_path, ALLOWED_HOSTS=value)


# ---------- 審查追加：SECRET_KEY 非空與熵、未知鍵 ----------


@pytest.mark.parametrize('app_env', ['development', 'test', 'production'])
def test_secret_key_must_not_be_empty(tmp_path: Path, app_env: str) -> None:
    with pytest.raises(ValidationError, match='SECRET_KEY'):
        make_settings(tmp_path, APP_ENV=app_env, SECRET_KEY='')


@pytest.mark.parametrize(
    'secret',
    [
        ' ' * 32,
        'a' * 32,
        'ab' * 32,
        string.ascii_letters[:9] * 4,  # 36 字元但只有 9 種不同字元
        ' ' + STRONG_SECRET,
        STRONG_SECRET + '\n',
    ],
)
def test_production_rejects_low_entropy_secret_key(tmp_path: Path, secret: str) -> None:
    with pytest.raises(ValidationError, match='SECRET_KEY'):
        make_settings(tmp_path, **production_overrides(SECRET_KEY=secret))


def test_production_accepts_secret_key_with_10_distinct_chars(tmp_path: Path) -> None:
    secret = string.ascii_letters[:10] * 4
    settings = make_settings(tmp_path, **production_overrides(SECRET_KEY=secret))
    assert len(set(settings.SECRET_KEY.get_secret_value())) == 10


def test_unknown_key_in_env_file_fails_without_leaking_value(tmp_path: Path) -> None:
    env_file = tmp_path / '.env'
    env_file.write_text('SECRET_KEY=dev\nSESSION_COOKIE_SECUR=leaked-typo-value-123\n', encoding='utf-8')
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=env_file)
    message = str(exc_info.value)
    assert 'SESSION_COOKIE_SECUR' in message
    assert 'leaked-typo-value-123' not in message


def test_unknown_init_key_fails(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        make_settings(tmp_path, NOT_A_SETTING='value')


def test_unrelated_environment_variables_are_ignored(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv('SOME_OTHER_TOOL_SETTING', 'x')
    assert make_settings(tmp_path).APP_ENV == 'test'


def test_production_accepts_hex_secret_key(tmp_path: Path) -> None:
    # token_hex 只有 0-9a-f 16 種字元；門檻 10 不可擋下 hex 金鑰（Code Review 第 2 輪 Major）
    fixed_hex = '0123456789abcdef' * 4
    assert make_settings(tmp_path, **production_overrides(SECRET_KEY=fixed_hex)).is_production
    for _ in range(200):
        make_settings(tmp_path, **production_overrides(SECRET_KEY=secrets.token_hex(32)))
