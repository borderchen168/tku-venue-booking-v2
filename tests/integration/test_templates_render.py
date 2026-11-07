"""T-002 樣板渲染測試：base.html、錯誤頁、靜態檔（routes.md 第 3 節、error-handling.md 第 3 節、style-guide.md 第 9、10 節）。

一律以實際的 `app.core.templating.templates`（含 context processor `app_context` 與 filter）渲染。
`request.state.skip_flash` 由 T-007 實作，本檔不測。
"""

import re
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

from app.core.templating import templates
from tests.fixtures.templates import (
    ERROR_STATUSES,
    TITLE_SEPARATOR,
    element_text,
    find_tag,
    find_tags,
    glued_lines,
    logged_in_state,
    make_request,
    render_file,
    render_source,
)

# 依 base.html 註解與 style-guide 7.6 的子樣板寫法：content 區塊標籤各自獨佔一行
CHILD_PAGE = (
    "{% extends 'base.html' %}\n"
    f'{{% block title %}}測試頁{TITLE_SEPARATOR}{{{{ super() }}}}{{% endblock %}}\n'
    '{% block content %}\n'
    '<h1>測試內容</h1>\n'
    '{% endblock %}\n'
)

# error-handling.md 第 3 節「呈現」欄的訊息文字
EXPECTED_ERROR_MESSAGES: dict[int, str] = {
    400: '請求格式不正確',
    403: '您沒有權限執行此操作',
    404: '找不到您要的頁面',
    413: '送出的資料過大',
    422: '請求內容格式不正確',
    500: '系統發生錯誤，請稍後再試',
    503: '系統忙碌，請稍後再試',
}
CSRF_MESSAGE = '表單已失效，請重新整理頁面後再試'

SENTINEL = 'SENTINEL-7f3a<b>leak</b>'


def error_template(status: int) -> str:
    return f'errors/{status}.html'


def nav_hrefs(html: str) -> list[str]:
    """主要導覽列（`<nav aria-label="主要導覽">`）內的連結。"""
    match = re.search(r'<nav class="site-nav" aria-label="主要導覽">(.*?)</nav>', html, re.DOTALL)
    assert match is not None
    return re.findall(r'href="([^"]*)"', match.group(1))


def assert_guest_header(html: str) -> None:
    login = find_tag(html, 'a', href='/login')
    assert login['class'] == 'button button--on-dark'
    assert element_text(html, 'a', href='/login') == '登入'
    assert '登出' not in html
    assert 'action="/logout"' not in html
    assert 'name="csrf_token"' not in html
    assert nav_hrefs(html) == ['/venues']


# ---------- base.html：訪客 / 缺少 request.state 屬性 ----------


def test_base_child_renders_as_guest_without_state() -> None:
    request = make_request('/')
    html = render_source(request, CHILD_PAGE)

    assert '<html lang="zh-Hant-TW">' in html
    assert f'<title>測試頁{TITLE_SEPARATOR}淡江場地預約系統</title>' in html
    assert '<h1>測試內容</h1>' in html
    assert '<main id="main"' in html
    assert_guest_header(html)
    # 未給 app → app_timezone 為預設值，顯示於頁尾
    assert '時間皆以 Asia/Taipei 時區顯示' in html


def test_base_html_renders_directly_as_guest() -> None:
    html = render_file(make_request('/'), 'base.html')
    assert '<title>淡江場地預約系統</title>' in html
    assert_guest_header(html)


def test_base_html_renders_without_any_context() -> None:
    """request、current_user、csrf_token、messages、app_timezone 全部未定義時仍可渲染（error-handling.md 3.2）。"""
    html = templates.env.get_template('base.html').render()
    assert_guest_header(html)
    assert '時區顯示' not in html


def test_base_html_renders_with_all_context_none() -> None:
    html = templates.env.get_template('base.html').render(
        request=None, current_user=None, csrf_token=None, messages=None, app_timezone=None
    )
    assert_guest_header(html)
    assert 'flash-list' not in html


def test_base_html_uses_app_timezone_from_settings(app: FastAPI) -> None:
    html = render_file(make_request('/', app=app), 'base.html')
    assert f'時間皆以 {app.state.settings.APP_TIMEZONE} 時區顯示' in html


@pytest.mark.parametrize('status', ERROR_STATUSES)
def test_error_page_renders_as_guest_without_state(status: int) -> None:
    html = render_file(make_request('/'), error_template(status))
    assert_guest_header(html)
    assert 'flash-list' not in html


# ---------- base.html：依角色顯示選單 ----------


def test_student_nav_has_only_booking_entry() -> None:
    html = render_source(make_request('/', **logged_in_state('student', display_name='王小明')), CHILD_PAGE)

    assert nav_hrefs(html) == ['/venues', '/bookings/new']
    assert '申請場地' in html
    assert '不開放期間管理' not in html
    assert '/admin/closed-periods' not in html


def test_staff_nav_has_only_closed_periods_entry() -> None:
    html = render_source(make_request('/', **logged_in_state('staff', display_name='陳承辦')), CHILD_PAGE)

    assert nav_hrefs(html) == ['/venues', '/admin/closed-periods']
    assert '不開放期間管理' in html
    assert '申請場地' not in html
    assert '/bookings/new' not in html


@pytest.mark.parametrize('role', ['student', 'staff'])
def test_unimplemented_menu_items_hidden(role: str) -> None:
    """Sprint 1 未實作的「我的申請」（US-005）、「待審核」（US-006）不顯示（US-013 AC1）。"""
    html = render_source(make_request('/', **logged_in_state(role)), CHILD_PAGE)
    assert '我的申請' not in html
    assert '待審核' not in html
    assert '即將推出' not in html
    assert '/bookings/mine' not in html
    assert '/admin/bookings' not in html


@pytest.mark.parametrize('role', ['student', 'staff'])
def test_logged_in_shows_logout_form_with_csrf_token(role: str) -> None:
    html = render_source(make_request('/', **logged_in_state(role, csrf='tok-123', display_name='王小明')), CHILD_PAGE)

    form = re.search(r'<form[^>]*action="/logout"[^>]*>(.*?)</form>', html, re.DOTALL)
    assert form is not None
    assert find_tag(form.group(0), 'form')['method'] == 'post'
    token = find_tag(form.group(1), 'input', name='csrf_token')
    assert token['type'] == 'hidden'
    assert token['value'] == 'tok-123'
    assert '登出' in form.group(1)
    assert 'href="/login"' not in html
    assert '王小明' in html


def test_logged_in_user_with_no_role_flags_sees_only_public_nav() -> None:
    """角色旗標皆為 False（預設拒絕）時不顯示任何角色選單，但仍可登出。"""
    user = SimpleNamespace(id=9, username='x', display_name='X', role='unknown', is_staff=False, is_student=False)
    html = render_source(make_request('/', current_user=user, session=SimpleNamespace(csrf_token='t')), CHILD_PAGE)
    assert nav_hrefs(html) == ['/venues']
    assert 'action="/logout"' in html


def test_display_name_is_escaped() -> None:
    payload = '"><script>alert(1)</script>'
    html = render_source(make_request('/', **logged_in_state('student', display_name=payload)), CHILD_PAGE)
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html


@pytest.mark.parametrize(
    ('path', 'href', 'expected'),
    [
        ('/venues', '/venues', 'aria-current="page"'),
        ('/venues/3/availability', '/venues', 'aria-current="true"'),
        ('/admin/closed-periods/new', '/admin/closed-periods', 'aria-current="true"'),
    ],
)
def test_nav_aria_current(path: str, href: str, expected: str) -> None:
    html = render_source(make_request(path, **logged_in_state('staff')), CHILD_PAGE)
    assert f'href="{href}" {expected}>' in html


def test_nav_aria_current_not_set_for_prefix_lookalike() -> None:
    """`/venuesX` 不是 `/venues` 的子頁面。"""
    html = render_source(make_request('/venuesX'), CHILD_PAGE)
    assert 'aria-current' not in html


# ---------- base.html：flash（樣板端防護；messages 實際來源由 T-007 處理） ----------


def test_flash_messages_render_with_level_whitelist() -> None:
    messages = [
        SimpleNamespace(level='success', text='已送出'),
        SimpleNamespace(level='error', text='失敗'),
        SimpleNamespace(level='" onclick="x', text='<script>alert(1)</script>'),
    ]
    html = templates.env.get_template('base.html').render(messages=messages)
    assert find_tag(html, 'div', **{'class': 'flash flash--success'})['role'] == 'status'
    assert find_tag(html, 'div', **{'class': 'flash flash--error'})['role'] == 'alert'
    # 非白名單 level 一律退回 info，不輸出原值
    assert find_tag(html, 'div', **{'class': 'flash flash--info'})['role'] == 'status'
    assert [d['class'] for d in find_tags(html, 'div') if (d['class'] or '').startswith('flash ')] == [
        'flash flash--success',
        'flash flash--error',
        'flash flash--info',
    ]
    assert 'onclick' not in html
    assert '<script>alert(1)</script>' not in html


# ---------- 錯誤頁 ----------


@pytest.mark.parametrize('status', ERROR_STATUSES)
def test_error_page_has_home_link_and_single_h1(status: int) -> None:
    html = render_file(make_request('/'), error_template(status))
    home = find_tag(html, 'a', href='/', **{'class': 'button'})
    assert home is not None
    assert element_text(html, 'a', href='/', **{'class': 'button'}) == '回首頁'
    assert html.count('<h1>') == 1
    assert '<title>' in html
    assert f'{TITLE_SEPARATOR}淡江場地預約系統</title>' in html


@pytest.mark.parametrize('status', ERROR_STATUSES)
def test_error_page_message_matches_spec(status: int) -> None:
    html = render_file(make_request('/'), error_template(status))
    assert EXPECTED_ERROR_MESSAGES[status] in html
    assert f'{status} ' in html


@pytest.mark.parametrize('status', ERROR_STATUSES)
def test_error_page_hint_rendered_at_most_once(status: int) -> None:
    """error_hint 區塊只經 self.error_hint() 輸出一次，不會在 </html> 之後重複出現。"""
    html = render_file(make_request('/'), error_template(status))
    assert html.rstrip().endswith('</html>')
    hint_paragraphs = re.findall(r'<p>([^<]+)</p>', html.split('<div class="error-page">', 1)[1])
    assert len(hint_paragraphs) == len(set(hint_paragraphs))


@pytest.mark.parametrize('status', ERROR_STATUSES)
def test_error_page_shows_request_id_from_context(status: int) -> None:
    html = render_file(make_request('/'), error_template(status), {'request_id': 'abc123def4567890'})
    assert '錯誤代碼：<code>abc123def4567890</code>' in html


@pytest.mark.parametrize('status', ERROR_STATUSES)
def test_error_page_falls_back_to_state_request_id(status: int) -> None:
    html = render_file(make_request('/', request_id='0123456789abcdef'), error_template(status), {'request_id': None})
    assert '錯誤代碼：<code>0123456789abcdef</code>' in html


def test_error_page_context_request_id_takes_precedence() -> None:
    html = render_file(make_request('/', request_id='fromstate'), 'errors/500.html', {'request_id': 'fromcontext'})
    assert 'fromcontext' in html
    assert 'fromstate' not in html


@pytest.mark.parametrize('status', ERROR_STATUSES)
@pytest.mark.parametrize('context', [{}, {'request_id': None}, {'request_id': ''}])
def test_error_page_without_request_id_hides_error_code(status: int, context: dict[str, Any]) -> None:
    html = render_file(make_request('/'), error_template(status), context)
    assert '錯誤代碼' not in html
    assert 'error-page__code' not in html


def test_error_page_request_id_is_escaped() -> None:
    html = render_file(make_request('/'), 'errors/500.html', {'request_id': '<script>alert(1)</script>'})
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;' in html


def test_500_hint_does_not_depend_on_error_code() -> None:
    """錯誤代碼不一定存在，提示文字不得寫「下方錯誤代碼」之類的指涉（500.html 註解、style-guide 第 10 節）。"""
    html = render_file(make_request('/'), 'errors/500.html')
    assert '下方' not in html
    assert '錯誤代碼' not in html


def test_403_csrf_variant() -> None:
    html = render_file(make_request('/'), 'errors/403.html', {'error_kind': 'csrf'})
    assert CSRF_MESSAGE in html
    assert f'<title>表單已失效{TITLE_SEPARATOR}淡江場地預約系統</title>' in html
    assert '<h1>表單已失效</h1>' in html
    assert '您沒有權限執行此操作' not in html


@pytest.mark.parametrize('context', [{}, {'error_kind': None}, {'error_kind': 'CSRF'}, {'error_kind': 'other'}])
def test_403_permission_variant(context: dict[str, Any]) -> None:
    """只有 `error_kind == 'csrf'` 切換為 CSRF 訊息，其他值一律顯示權限訊息（routes.md 3.2）。"""
    html = render_file(make_request('/'), 'errors/403.html', context)
    assert '您沒有權限執行此操作' in html
    assert '<h1>沒有權限</h1>' in html
    assert '表單已失效' not in html


@pytest.mark.parametrize('status', ERROR_STATUSES)
def test_error_page_does_not_output_exception_details(status: int) -> None:
    """handler 誤傳的例外訊息、reason、路徑或使用者輸入都不會出現在畫面（error-handling.md 第 1 節原則 3）。"""
    context = {
        'message': SENTINEL,
        'detail': SENTINEL,
        'reason': SENTINEL,
        'exc': RuntimeError(SENTINEL),
        'error': SENTINEL,
        'path': SENTINEL,
        'form': {'username': SENTINEL},
        'errors': {'__all__': SENTINEL},
    }
    html = render_file(make_request('/SENTINEL-7f3a'), error_template(status), context)
    assert 'SENTINEL' not in html
    assert 'RuntimeError' not in html
    assert 'Traceback' not in html


@pytest.mark.parametrize('status', ERROR_STATUSES)
@pytest.mark.parametrize('role', ['student', 'staff'])
def test_error_page_logged_in_keeps_role_nav(status: int, role: str) -> None:
    html = render_file(make_request('/', **logged_in_state(role, csrf='err-tok')), error_template(status))
    assert '<input type="hidden" name="csrf_token" value="err-tok">' in html
    assert len(nav_hrefs(html)) == 2


@pytest.mark.parametrize('status', ERROR_STATUSES)
def test_error_page_renders_with_empty_messages(status: int) -> None:
    request = make_request('/', **logged_in_state('student'))
    response = templates.TemplateResponse(request, error_template(status), {})
    assert response.context['messages'] == []
    assert 'flash-list' not in bytes(response.body).decode('utf-8')


# ---------- 空白控制回歸（style-guide 7.6）：每個 HTML 標籤獨立一行 ----------


@pytest.mark.parametrize('status', ERROR_STATUSES)
@pytest.mark.parametrize('state', [{}, logged_in_state('student'), logged_in_state('staff')], ids=['guest', 'student', 'staff'])
def test_error_page_tags_not_glued(status: int, state: dict[str, Any]) -> None:
    html = render_file(make_request('/', **state), error_template(status), {'request_id': 'abc123', 'error_kind': 'csrf'})
    assert glued_lines(html) == []


@pytest.mark.parametrize('role', ['student', 'staff'])
def test_base_layout_tags_not_glued(role: str) -> None:
    html = render_source(make_request('/', **logged_in_state(role)), CHILD_PAGE)
    assert glued_lines(html) == []
    assert html.startswith('<!DOCTYPE html>')
    # 子樣板依約定撰寫時，</main> 從新的一行開始
    assert re.search(r'\n\s*</main>', html)
    assert re.search(r'\n<h1>測試內容</h1>\n', html)


def test_flash_messages_not_glued() -> None:
    messages = [SimpleNamespace(level='success', text='一'), SimpleNamespace(level='info', text='二')]
    html = templates.env.get_template('base.html').render(messages=messages)
    assert glued_lines(html) == []
    assert html.count('\n') > 20


def test_glued_lines_detects_regression() -> None:
    """負面測試：確認檢查規則本身能抓到黏行。"""
    assert glued_lines('<li>a</li>                    <li>b</li>') != []
    assert glued_lines('<p>a</p><p class="x">b</p>') != []
    assert glued_lines('<li>a</li>\n<li>b</li>\n<p>a</p>\n<pre>x</pre>') == []


# ---------- 透過 TestClient 的端對端渲染 ----------


@pytest.fixture
def render_client(app: FastAPI) -> TestClient:
    """掛上測試用 route：渲染指定錯誤頁，`request.state` 不設任何屬性（模擬 Session 載入前的 500）。"""

    def render_error(request: Request, status: int) -> HTMLResponse:
        if status not in ERROR_STATUSES:
            return HTMLResponse('', status_code=400)
        return templates.TemplateResponse(request, error_template(status), {'request_id': None}, status_code=status)

    app.add_api_route('/_test/errors/{status}', render_error, methods=['GET'], response_class=HTMLResponse)
    return TestClient(app)


@pytest.mark.parametrize('status', ERROR_STATUSES)
def test_error_page_via_client(render_client: TestClient, status: int) -> None:
    response = render_client.get(f'/_test/errors/{status}')
    assert response.status_code == status
    assert response.headers['content-type'].startswith('text/html')
    assert EXPECTED_ERROR_MESSAGES[status] in response.text
    assert_guest_header(response.text)


# ---------- 靜態檔 ----------


def test_main_css_served(client: TestClient) -> None:
    response = client.get('/static/css/main.css')
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/css')
    assert '.site-header' in response.text


def test_favicon_served(client: TestClient) -> None:
    response = client.get('/static/img/favicon.svg')
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('image/svg+xml')
