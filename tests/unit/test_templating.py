"""templating 測試：autoescape、context processor、filter（routes.md 第 3 節、error-handling.md 3.2）。"""

import datetime as dt
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import jinja2
import pytest
from fastapi import FastAPI
from starlette.requests import Request

from app.core import templating
from app.core.templating import (
    CATEGORY_LABELS,
    REASON_TYPE_LABELS,
    STATUS_LABELS,
    TEMPLATES_DIR,
    app_context,
    build_environment,
    templates,
)
from tests.fixtures.settings import make_settings


def make_request(app: FastAPI | None = None, **state: Any) -> Request:
    scope: dict[str, Any] = {'type': 'http', 'method': 'GET', 'path': '/', 'headers': [], 'query_string': b''}
    if app is not None:
        scope['app'] = app
    request = Request(scope)
    for key, value in state.items():
        setattr(request.state, key, value)
    return request


@pytest.fixture
def env(tmp_path: Path) -> jinja2.Environment:
    return build_environment(tmp_path)


def render(env: jinja2.Environment, source: str, **context: Any) -> str:
    return env.from_string(source).render(**context)


def test_templates_dir_points_to_app_templates() -> None:
    assert Path(templating.__file__).resolve().parent.parent / 'templates' == TEMPLATES_DIR
    assert templates.env.autoescape is True


def test_autoescape_enabled(env: jinja2.Environment) -> None:
    assert env.autoescape is True
    assert render(env, '{{ value }}', value='<script>alert(1)</script>') == '&lt;script&gt;alert(1)&lt;/script&gt;'


def test_autoescape_applies_to_file_templates(tmp_path: Path) -> None:
    (tmp_path / 'page.txt').write_text('{{ value }}', encoding='utf-8')
    env = build_environment(tmp_path)
    assert env.get_template('page.txt').render(value='<b>') == '&lt;b&gt;'


def test_context_without_state_attributes_is_anonymous() -> None:
    context = app_context(make_request())
    assert context['current_user'] is None
    assert context['csrf_token'] is None
    assert context['messages'] == []
    assert context['app_timezone'] == 'Asia/Taipei'


def test_context_with_none_state_is_anonymous() -> None:
    context = app_context(make_request(current_user=None, session=None))
    assert context['current_user'] is None
    assert context['csrf_token'] is None


def test_context_logged_in_uses_session_token() -> None:
    user = SimpleNamespace(id=1, username='s1', display_name='王小明', role='student')
    session = SimpleNamespace(csrf_token='session-token')
    context = app_context(make_request(current_user=user, session=session, login_csrf_token='login-token'))
    assert context['current_user'] is user
    assert context['csrf_token'] == 'session-token'


def test_context_login_page_uses_login_token() -> None:
    context = app_context(make_request(login_csrf_token='login-token'))
    assert context['current_user'] is None
    assert context['csrf_token'] == 'login-token'


def test_context_uses_app_settings_timezone(tmp_path: Path) -> None:
    app = FastAPI()
    app.state.settings = make_settings(tmp_path, APP_TIMEZONE='UTC')
    assert app_context(make_request(app))['app_timezone'] == 'UTC'


def test_context_app_without_settings_uses_default() -> None:
    assert app_context(make_request(FastAPI()))['app_timezone'] == 'Asia/Taipei'


def test_template_response_renders_anonymous_without_state(tmp_path: Path) -> None:
    (tmp_path / 'nav.html').write_text(
        '{% if current_user %}hi {{ current_user.display_name }}{% else %}guest{% endif %}|{{ csrf_token or "" }}|{{ messages|length }}',
        encoding='utf-8',
    )
    local = templating.Jinja2Templates(env=build_environment(tmp_path), context_processors=[app_context])
    response = local.TemplateResponse(make_request(), 'nav.html')
    assert response.body.decode('utf-8') == 'guest||0'


def test_local_dt_filter(env: jinja2.Environment) -> None:
    moment = dt.datetime(2026, 11, 15, 16, 30, tzinfo=dt.UTC)
    assert render(env, '{{ m|local_dt }}', m=moment, app_timezone='Asia/Taipei') == '2026-11-16 00:30'
    assert render(env, '{{ m|local_dt }}', m=moment, app_timezone='UTC') == '2026-11-15 16:30'
    assert render(env, '{{ m|local_dt }}', m=moment) == '2026-11-16 00:30'
    assert render(env, '{{ m|local_dt }}', m=None) == ''


def test_local_dt_rejects_naive(env: jinja2.Environment) -> None:
    naive = dt.datetime(2026, 11, 15, 16, 30, tzinfo=dt.UTC).replace(tzinfo=None)
    with pytest.raises(ValueError, match='naive'):
        render(env, '{{ m|local_dt }}', m=naive)


def test_local_date_filter(env: jinja2.Environment) -> None:
    moment = dt.datetime(2026, 11, 15, 16, 30, tzinfo=dt.UTC)
    assert render(env, '{{ m|local_date }}', m=moment) == '2026-11-16'
    assert render(env, '{{ d|local_date }}', d=dt.date(2026, 11, 15)) == '2026-11-15'
    assert render(env, '{{ d|local_date }}', d=None) == ''


def test_hhmm_filter(env: jinja2.Environment) -> None:
    assert render(env, '{{ t|hhmm }}', t=dt.time(8, 0)) == '08:00'
    assert render(env, '{{ m|hhmm }}', m=dt.datetime(2026, 11, 16, 14, 0, tzinfo=dt.UTC)) == '22:00'
    assert render(env, '{{ t|hhmm }}', t=None) == ''


@pytest.mark.parametrize(
    ('filter_name', 'labels'),
    [('status_label', STATUS_LABELS), ('reason_type_label', REASON_TYPE_LABELS), ('category_label', CATEGORY_LABELS)],
)
def test_label_filters(env: jinja2.Environment, filter_name: str, labels: dict[str, str]) -> None:
    for value, label in labels.items():
        assert render(env, f'{{{{ v|{filter_name} }}}}', v=value) == label
    assert render(env, f'{{{{ v|{filter_name} }}}}', v='<unknown>') == '&lt;unknown&gt;'
    assert render(env, f'{{{{ v|{filter_name} }}}}', v=None) == ''


def test_label_values_match_erd() -> None:
    assert set(STATUS_LABELS) == {'pending', 'approved', 'rejected', 'cancelled'}
    assert set(REASON_TYPE_LABELS) == {'national_holiday', 'exam_week', 'major_exam', 'other'}
    assert set(CATEGORY_LABELS) == {'club_activity', 'stall'}


def test_weekday_label(env: jinja2.Environment) -> None:
    assert render(env, '{{ d|weekday_label }}', d=dt.date(2026, 11, 16)) == '一'
    assert render(env, '{{ d|weekday_label }}', d=dt.date(2026, 11, 22)) == '日'
    assert render(env, '{{ i|weekday_label }}', i=5) == '六'


@pytest.mark.parametrize('value', [-1, 7, 100])
def test_weekday_label_rejects_out_of_range(env: jinja2.Environment, value: int) -> None:
    with pytest.raises(ValueError, match='0～6'):
        render(env, '{{ i|weekday_label }}', i=value)


def test_context_session_without_token_has_no_csrf_token() -> None:
    context = app_context(make_request(session=SimpleNamespace(), login_csrf_token='login-token'))
    assert context['csrf_token'] is None


def test_context_ignores_non_string_tokens() -> None:
    assert app_context(make_request(session=SimpleNamespace(csrf_token=123)))['csrf_token'] is None
    assert app_context(make_request(login_csrf_token=b'bytes'))['csrf_token'] is None


def test_macro_imported_with_context_uses_app_timezone(tmp_path: Path) -> None:
    (tmp_path / 'macros.html').write_text('{% macro when(m) %}{{ m|local_dt }}{% endmacro %}', encoding='utf-8')
    (tmp_path / 'with.html').write_text("{% import 'macros.html' as mc with context %}{{ mc.when(m) }}", encoding='utf-8')
    (tmp_path / 'without.html').write_text("{% import 'macros.html' as mc %}{{ mc.when(m) }}", encoding='utf-8')
    env = build_environment(tmp_path)
    moment = dt.datetime(2026, 11, 15, 16, 30, tzinfo=dt.UTC)
    assert env.get_template('with.html').render(m=moment, app_timezone='UTC') == '2026-11-15 16:30'
    # 未帶 context：filter 取不到 app_timezone，退回預設 Asia/Taipei（模組 docstring 說明的行為）
    assert env.get_template('without.html').render(m=moment, app_timezone='UTC') == '2026-11-16 00:30'


def test_context_keys_are_exactly_documented_set() -> None:
    assert set(app_context(make_request())) == {'current_user', 'csrf_token', 'messages', 'app_timezone'}
