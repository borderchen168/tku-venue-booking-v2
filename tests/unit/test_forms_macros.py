"""`macros/forms.html` 測試（style-guide.md 第 7 節、routes.md 第 3、4 節）。

以實際的 Jinja2 環境與 context processor 渲染（`with context` 匯入，巨集才讀得到 `csrf_token`、`form`、`errors`）。
斷言先以 `find_tag` 解析出標籤再逐一檢查屬性，不依賴空白與換行（style-guide 7.6 可能調整空白控制）。
XSS 檢查則直接比對原始輸出，確認 payload 已被 escape。
"""

from typing import Any

import pytest

from tests.fixtures.templates import element_text, find_tag, find_tags, glued_lines, logged_in_state, make_request, render_source

IMPORT = "{% import 'macros/forms.html' as forms with context %}\n"
XSS = '"><script>alert(1)</script>'
XSS_ESCAPED = '&#34;&gt;&lt;script&gt;alert(1)&lt;/script&gt;'
SVG_PAYLOAD = '"><svg onload=alert(1)>'


def render(body: str, state: dict[str, Any] | None = None, **context: Any) -> str:
    return render_source(make_request('/', **(state or {})), IMPORT + body, **context)


def control(html: str, tag: str = 'input') -> dict[str, str | None]:
    """欄位控制項（`class` 以 `field__control` 開頭的 input / textarea / select）。"""
    found = [attrs for attrs in find_tags(html, tag) if (attrs.get('class') or '').startswith('field__control')]
    assert len(found) == 1
    return found[0]


# ---------- input ----------


def test_input_without_error_has_no_aria_invalid() -> None:
    html = render("{{ forms.input('username', '帳號', required=true) }}", form={'username': 'alice'})
    tag = control(html)
    assert tag['id'] == 'field-username'
    assert tag['name'] == 'username'
    assert tag['type'] == 'text'
    assert tag['value'] == 'alice'
    assert 'required' in tag
    assert 'aria-invalid' not in tag
    assert 'aria-describedby' not in tag
    assert find_tag(html, 'div')['class'] == 'field'
    assert find_tag(html, 'label')['for'] == 'field-username'
    assert element_text(html, 'label') == '帳號（必填）'


def test_input_with_error_sets_aria_invalid_and_describedby() -> None:
    html = render("{{ forms.input('username', '帳號') }}", errors={'username': '請輸入帳號'})
    tag = control(html)
    assert tag['aria-invalid'] == 'true'
    assert tag['aria-describedby'] == 'field-username-error'
    assert find_tag(html, 'p', id='field-username-error')['class'] == 'field__error'
    assert element_text(html, 'p', id='field-username-error') == '錯誤：請輸入帳號'
    assert find_tag(html, 'div')['class'] == 'field field--error'


def test_input_help_and_error_both_described() -> None:
    html = render("{{ forms.input('date', '日期', type='date', help='YYYY-MM-DD') }}", errors={'date': '日期格式錯誤'})
    tag = control(html)
    assert tag['type'] == 'date'
    assert tag['aria-describedby'] == 'field-date-help field-date-error'
    assert find_tag(html, 'p', id='field-date-help')['class'] == 'field__help'
    find_tag(html, 'p', id='field-date-error')


def test_input_custom_id_used_for_error_reference() -> None:
    html = render("{{ forms.input('username', '帳號', id='login-user') }}", errors={'username': '錯誤'})
    tag = control(html)
    assert tag['id'] == 'login-user'
    assert tag['aria-describedby'] == 'login-user-error'
    find_tag(html, 'p', id='login-user-error')
    assert find_tag(html, 'label')['for'] == 'login-user'


def test_input_empty_error_message_ignored() -> None:
    html = render("{{ forms.input('username', '帳號') }}", errors={'username': ''})
    assert 'aria-invalid' not in control(html)
    assert 'field__error' not in html


@pytest.mark.parametrize('form', [{'password': 'secret-pass'}, {}])
def test_password_never_outputs_value(form: dict[str, str]) -> None:
    html = render("{{ forms.input('password', '密碼', type='password', value='explicit-secret') }}", form=form)
    tag = control(html)
    assert tag['type'] == 'password'
    assert 'value' not in tag
    assert 'secret' not in html


def test_password_with_error_still_no_value() -> None:
    html = render("{{ forms.input('password', '密碼', type='password') }}", form={'password': 'p@ss'}, errors={'password': '錯誤'})
    tag = control(html)
    assert 'value' not in tag
    assert tag['aria-invalid'] == 'true'
    assert 'p@ss' not in html


def test_input_explicit_value_overrides_form() -> None:
    html = render("{{ forms.input('username', '帳號', value='explicit') }}", form={'username': 'from-form'})
    assert control(html)['value'] == 'explicit'
    assert 'from-form' not in html


@pytest.mark.parametrize('bad_type', ['hidden', 'file', '" onfocus="x', 'checkbox'])
def test_input_type_whitelist(bad_type: str) -> None:
    html = render('{{ forms.input("q", "查詢", type=t) }}', t=bad_type)
    assert control(html)['type'] == 'text'
    assert 'onfocus' not in html


def test_input_value_and_label_escaped() -> None:
    html = render(
        "{{ forms.input('activity_name', label, help=label) }}", label=XSS, form={'activity_name': XSS}, errors={'activity_name': XSS}
    )
    assert '<script>' not in html
    assert html.count(XSS_ESCAPED) == 4  # label、help、error、value
    assert control(html)['value'] == XSS  # 解碼後仍完整留在 value 屬性內


# ---------- textarea / select ----------


def test_textarea_error_and_escape() -> None:
    html = render("{{ forms.textarea('description', '說明') }}", form={'description': XSS}, errors={'description': '太長'})
    tag = control(html, 'textarea')
    assert '<script>' not in html
    assert tag['aria-invalid'] == 'true'
    assert tag['aria-describedby'] == 'field-description-error'
    assert tag['rows'] == '5'
    assert f'>{XSS_ESCAPED}</textarea>' in html


def test_select_marks_selected_and_escapes() -> None:
    html = render(
        "{{ forms.select('reason_type', '原因', options) }}",
        options=[('exam_week', '考試週'), (XSS, XSS)],
        form={'reason_type': 'exam_week'},
        errors={'reason_type': '請選擇'},
    )
    assert 'selected' in find_tag(html, 'option', value='exam_week')
    # 已有選值時 placeholder 不標 selected
    assert 'selected' not in find_tag(html, 'option', value='')
    assert 'selected' not in find_tag(html, 'option', value=XSS)
    assert '<script>' not in html
    assert control(html, 'select')['aria-invalid'] == 'true'


def selected_values(html: str) -> list[str | None]:
    return [attrs['value'] for attrs in find_tags(html, 'option') if 'selected' in attrs]


def test_select_int_options_match_string_form_value() -> None:
    """form 的值皆為字串，options 的值可能是 int（社團 id）：以字串比較（forms.html select 說明）。"""
    html = render("{{ forms.select('club_id', '社團', options) }}", options=[(1, 'A'), (2, 'B')], form={'club_id': '2'})
    assert selected_values(html) == ['2']


def test_select_explicit_int_value_selected() -> None:
    html = render("{{ forms.select('club_id', '社團', options, value=2) }}", options=[(1, 'A'), (2, 'B')], form={'club_id': '1'})
    assert selected_values(html) == ['2']


def test_select_without_value_selects_placeholder() -> None:
    html = render("{{ forms.select('club_id', '社團', options) }}", options=[(1, 'A'), (2, 'B')])
    assert selected_values(html) == ['']
    assert element_text(html, 'option', value='') == '請選擇'


def test_select_placeholder_none_outputs_no_empty_option() -> None:
    html = render("{{ forms.select('club_id', '社團', options, placeholder=none) }}", options=[(1, 'A'), (2, 'B')])
    assert [attrs['value'] for attrs in find_tags(html, 'option')] == ['1', '2']
    assert selected_values(html) == []


# ---------- form_errors ----------


def test_form_errors_lists_global_and_field_errors() -> None:
    errors = {'__all__': '該時段已被借用', 'date': '日期格式錯誤', 'venue_id': '請選擇場地'}
    html = render('{{ forms.form_errors() }}', errors=errors)
    summary = find_tag(html, 'div', id='error-summary')
    assert summary['class'] == 'error-summary'
    assert summary['role'] == 'alert'
    assert summary['aria-labelledby'] == 'error-summary-title'
    assert find_tag(html, 'h2', id='error-summary-title')['class'] == 'error-summary__title'
    assert element_text(html, 'h2') == '送出失敗，請修正以下問題'
    assert element_text(html, 'p') == '該時段已被借用'
    assert [a['href'] for a in find_tags(html, 'a')] == ['#field-date', '#field-venue_id']
    assert element_text(html, 'a', href='#field-date') == '日期格式錯誤'
    assert element_text(html, 'a', href='#field-venue_id') == '請選擇場地'


def test_form_errors_ignores_empty_messages() -> None:
    html = render('{{ forms.form_errors() }}', errors={'__all__': '', 'date': '', 'venue_id': '請選擇場地'})
    assert len(find_tags(html, 'li')) == 1
    assert find_tags(html, 'p') == []
    assert '#field-date' not in html


@pytest.mark.parametrize('errors', [{}, {'__all__': '', 'date': ''}, None])
def test_form_errors_renders_nothing_without_messages(errors: dict[str, str] | None) -> None:
    context = {} if errors is None else {'errors': errors}
    html = render('{{ forms.form_errors() }}', **context)
    assert html.strip() == ''


def test_form_errors_only_global() -> None:
    html = render('{{ forms.form_errors() }}', errors={'__all__': '系統忙碌，請稍後再試'})
    assert element_text(html, 'p') == '系統忙碌，請稍後再試'
    assert find_tags(html, 'ul') == []


def test_form_errors_custom_title_and_id() -> None:
    html = render("{{ forms.form_errors(title='無法顯示所選的週', id='week-errors') }}", errors={'week_start': '日期錯誤'})
    assert find_tag(html, 'div', id='week-errors')['aria-labelledby'] == 'week-errors-title'
    find_tag(html, 'h2', id='week-errors-title')
    assert element_text(html, 'h2') == '無法顯示所選的週'
    assert find_tags(html, 'div', id='error-summary') == []


def test_form_errors_escapes_messages() -> None:
    html = render('{{ forms.form_errors() }}', errors={'__all__': XSS, 'date': XSS})
    assert '<script>' not in html
    assert html.count(XSS_ESCAPED) == 2


def test_form_errors_escapes_title_id_and_keys() -> None:
    html = render('{{ forms.form_errors(title=p, id=p) }}', p=SVG_PAYLOAD, errors={SVG_PAYLOAD: '錯誤'})
    assert '<svg' not in html
    assert find_tags(html, 'svg') == []
    # payload 完整留在屬性值內，沒有跳脫出屬性
    assert find_tag(html, 'div', id=SVG_PAYLOAD)['aria-labelledby'] == f'{SVG_PAYLOAD}-title'
    find_tag(html, 'h2', id=f'{SVG_PAYLOAD}-title')
    assert find_tag(html, 'a')['href'] == f'#field-{SVG_PAYLOAD}'
    assert element_text(html, 'h2') == SVG_PAYLOAD.replace('>', '&gt;').replace('<', '&lt;').replace('"', '&#34;')


def test_form_errors_default_id_duplicated_when_called_twice() -> None:
    """已記載的限制（forms.html form_errors 說明、style-guide 第 7 節）：同一頁呼叫兩次且都用預設 id 時，id 會重複。

    巨集無法得知同頁已輸出的 id，因此由呼叫端負責傳入不同的 `id`；本測試固定此行為，若巨集日後改為自動避開重複，
    請同步更新文件與本測試。
    """
    html = render('{{ forms.form_errors() }}\n{{ forms.form_errors() }}', errors={'__all__': '錯誤'})
    assert len(find_tags(html, 'div', id='error-summary')) == 2
    assert len(find_tags(html, 'h2', id='error-summary-title')) == 2

    html = render("{{ forms.form_errors() }}\n{{ forms.form_errors(id='second') }}", errors={'__all__': '錯誤'})
    assert len(find_tags(html, 'div', id='error-summary')) == 1
    assert len(find_tags(html, 'div', id='second')) == 1


# ---------- csrf_field / hidden / submit ----------


def hidden_input(html: str, name: str) -> dict[str, str | None]:
    tag = find_tag(html, 'input', name=name)
    assert tag['type'] == 'hidden'
    return tag


def test_csrf_field_outputs_session_token() -> None:
    html = render('{{ forms.csrf_field() }}', state=logged_in_state('student', csrf='tok-abc'))
    assert hidden_input(html, 'csrf_token')['value'] == 'tok-abc'
    assert len(find_tags(html, 'input')) == 1


def test_csrf_field_uses_login_token_when_anonymous() -> None:
    html = render('{{ forms.csrf_field() }}', state={'login_csrf_token': 'login-tok'})
    assert hidden_input(html, 'csrf_token')['value'] == 'login-tok'


def test_csrf_field_without_token_outputs_empty_value() -> None:
    html = render('{{ forms.csrf_field() }}')
    assert hidden_input(html, 'csrf_token')['value'] == ''


def test_csrf_field_escapes_token() -> None:
    html = render('{{ forms.csrf_field() }}', state=logged_in_state('student', csrf=XSS))
    assert '<script>' not in html
    assert XSS_ESCAPED in html
    assert hidden_input(html, 'csrf_token')['value'] == XSS


def test_hidden_escapes_value() -> None:
    html = render("{{ forms.hidden('next', next_path) }}", next_path=XSS)
    assert '<script>' not in html
    assert XSS_ESCAPED in html
    assert hidden_input(html, 'next')['value'] == XSS


def test_hidden_none_value_is_empty() -> None:
    assert hidden_input(render("{{ forms.hidden('next', none) }}"), 'next')['value'] == ''


@pytest.mark.parametrize(
    ('variant', 'expected_class'),
    [('primary', 'button'), ('secondary', 'button button--secondary'), ('danger', 'button button--danger'), ('x" onclick="y', 'button')],
)
def test_submit_variant_whitelist(variant: str, expected_class: str) -> None:
    html = render("{{ forms.submit('送出', variant=v) }}", v=variant)
    button = find_tag(html, 'button')
    assert button == {'type': 'submit', 'class': expected_class}
    assert element_text(html, 'button') == '送出'
    assert 'onclick' not in html


# ---------- 空白控制回歸（style-guide 7.6） ----------

FORM_PAGE = """<form method="post" action="/x">
{{ forms.csrf_field() }}
{{ forms.form_errors() }}
{{ forms.input('username', '帳號', required=true, help='說明') }}
{{ forms.textarea('description', '說明', help='說明') }}
{{ forms.select('club_id', '社團', options, help='說明') }}
{{ forms.submit('送出') }}
</form>
"""


def test_form_macros_output_one_tag_per_line() -> None:
    errors = {'__all__': '全域錯誤', 'username': '帳號錯誤', 'description': '說明錯誤', 'club_id': '社團錯誤'}
    html = render(FORM_PAGE, options=[(1, 'A'), (2, 'B')], errors=errors)
    assert glued_lines(html) == []
    # 巨集輸出之間不留空行
    assert '\n\n' not in html.strip()
    # 每個 HTML 開始標籤（行內的 <span>、<a>、<code> 除外）都在自己的一行
    for line in html.strip().splitlines():
        assert line.count('<') - line.count('</') - line.count('<span') - line.count('<a ') <= 1, line
