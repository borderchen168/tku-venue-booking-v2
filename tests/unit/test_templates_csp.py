"""CSP 相容性靜態檢查（T-002、overview.md 第 8 節、style-guide.md 第 12 節）。

## 掃描範圍
`TEMPLATES_DIR` 下的**所有**檔案（不限 `*.html`，一律視為 Jinja2 樣板）與 `app/static/**`。遇到無法以 UTF-8 解碼
或含 NUL 的二進位檔時，以明確訊息失敗（需要新增二進位靜態檔時，請同步調整本檢查）。

## 掃描片段（依檔案類型產生，註解只依該類型的語法剝除）
- **Jinja2 樣板**：以 Jinja2 lexer 切開（`{# #}` 由 lexer 丟棄）。
  - markup（兩份）：`data` token 依序串接，Jinja 標籤的位置(1) 補一個空白、(2) 以空字串串接，兩份都移除 `<!-- -->`。
    (2) 用來抓「以空的 Jinja 標籤切開關鍵字」，例如 `<scr{% if true %}{% endif %}ipt>`、`on{{ "" }}click=`。
    寫在 Jinja 運算式裡的註解標記（`{{ '<!--' }}`）不屬於 `data`，無法把後面的內容藏成註解。
    `/* */` 在 HTML 中不是註解，不剝除（`accept="image/*"` 不會吞掉後面的內容）。
  - url：上述兩份 markup 經 HTML entity 解碼，另各產生一份移除 `\t\n\r` 的版本（瀏覽器解析 URL 時會忽略這些字元）。
  - jinja：`{{ }}`、`{% %}` 內的 token 以空白串接。
- **CSS**：只剝除 `/* */`；markup、url、css 規則皆套用（CSS 不解碼 HTML entity）。
- **SVG**：只剝除 `<!-- -->` 並排除 `xmlns` 命名空間 URI；markup 規則套用原文，url 規則套用解碼後版本。
- 其他文字檔：不剝除，markup 與 url 規則套用原文。

## 規則分類（每條規則只套用在對應的片段，避免把 Jinja 變數名稱或已跳脫的文字誤判）
- **jinja**（只看 Jinja 程式碼）：`|safe` / `{% filter safe %}`、`Markup`、任何 `autoescape` 區塊、`xmlattr`、`__html__`。
- **markup**（只看未解碼的 markup）：禁用標籤（`<script`、`<style`、`<iframe`、`<base`、`<object`、`<embed`、
  meta refresh）、`srcdoc`、`on*=`、`style=`、`enctype`、`@import`、URL 屬性值含 `&#` 或 `&Tab;` 等 entity。
  已跳脫的文字（`&lt;script&gt;`）不會命中，因為標籤類規則不看解碼後的版本。
- **url**（只看 entity 解碼後的 markup）：`javascript:`、`data:`、載入資源的位置（`src`、`srcset`、`poster`、
  `formaction`、`<link href>`、`<form action>`、SVG `<image>` / `<use>` 的 `href`、CSS `url(`）使用任何 `scheme:`
  或以 `//`、`/\\`、`\\\\` 開頭；任何 `href` 以 `//`、`/\\`、`\\\\` 開頭。`<a href="https://…">` 外部**連結**允許。
- **css**（只看 CSS 檔）：反斜線 escape（`\\`）。

## 已知限制（需由 Code Review 把關）
- 以 Jinja 運算式動態組出的屬性名稱或值無法涵蓋，例如 `{{ 'on' ~ 'click' }}=`、`<{{ 'scr' ~ 'ipt' }}>`、
  `<img src="{{ 'https://evil.example/x.png' }}">`（運算式內的字串常值不納入 markup / url 掃描）。
- 以變數傳入的 URL（`<a href="{{ url }}">`）只能靠 route 端的驗證與 autoescape。
- 規則以 regex 比對，不是完整的 HTML / CSS parser；刻意的混淆（例如屬性名稱中插入 NUL 以外的奇特字元）仍需人工審查。
"""

import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pytest

from app.core.templating import TEMPLATES_DIR, templates
from app.main import STATIC_DIR

Category = Literal['jinja', 'markup', 'url', 'css']

_SCHEME_OR_SLASHES = r'["\']?\s*(?:[a-z][a-z0-9+.\-]*:|[/\\]{2})'
_SLASHES = r'["\']?\s*[/\\]{2}'


@dataclass(frozen=True)
class Rule:
    """一條掃描規則：`category` 決定套用在哪些片段。"""

    name: str
    category: Category
    pattern: re.Pattern[str]


def _rule(name: str, category: Category, pattern: str, flags: int = re.IGNORECASE) -> Rule:
    return Rule(name, category, re.compile(pattern, flags))


RULES: tuple[Rule, ...] = (
    # ---------- jinja ----------
    _rule('|safe', 'jinja', r'(?:\|\s*|\bfilter\s+)safe\b', 0),
    _rule('Markup', 'jinja', r'\bMarkup\b', 0),
    _rule('autoescape 區塊', 'jinja', r'\bautoescape\b'),
    _rule('xmlattr', 'jinja', r'\bxmlattr\b'),
    _rule('__html__', 'jinja', r'__html__'),
    # ---------- markup ----------
    _rule('<script', 'markup', r'<script'),
    _rule('<style', 'markup', r'<style'),
    _rule('style= 屬性', 'markup', r'(?<![\w-])style\s*='),
    _rule('on*= 事件屬性', 'markup', r'(?<![\w-])on\w+\s*='),
    _rule('meta refresh', 'markup', r'<meta\b[^>]*http-equiv\s*=\s*["\']?refresh'),
    _rule('<iframe', 'markup', r'<iframe'),
    _rule('srcdoc', 'markup', r'srcdoc'),
    _rule('<base', 'markup', r'<base\b'),
    _rule('<object', 'markup', r'<object'),
    _rule('<embed', 'markup', r'<embed'),
    _rule('enctype', 'markup', r'enctype'),
    _rule('@import', 'markup', r'@import'),
    _rule(
        'URL 屬性含 HTML entity',
        'markup',
        r'(?<![\w-])(?:href|src|srcset|poster|action|formaction)\s*=\s*["\']?[^"\'\s>]*&(?:#|tab;|newline;|colon;)',
    ),
    # ---------- url ----------
    _rule('javascript: URL', 'url', r'javascript:'),
    _rule('data: URI', 'url', r'(?<![\w-])data:'),
    _rule(
        '外部資源 URL',
        'url',
        r'(?:(?<![\w-])(?:src|poster|formaction)\s*=\s*'
        + _SCHEME_OR_SLASHES
        + r'|(?<![\w-])srcset\s*=\s*["\']?[^"\'>]*(?:[a-z][a-z0-9+.\-]*:|[/\\]{2})'
        + r'|<link\b[^>]*\shref\s*=\s*'
        + _SCHEME_OR_SLASHES
        + r'|<form\b[^>]*\saction\s*=\s*'
        + _SCHEME_OR_SLASHES
        + r'|<(?:image|use|feimage)\b[^>]*\s(?:xlink:)?href\s*=\s*'
        + _SCHEME_OR_SLASHES
        + r'|url\(\s*'
        + _SCHEME_OR_SLASHES
        + ')',
    ),
    _rule('href 協定相對 / 反斜線', 'url', r'(?<![\w-])href\s*=\s*' + _SLASHES),
    # ---------- css ----------
    _rule('CSS 反斜線 escape', 'css', r'\\', 0),
)
RULE_NAMES = {rule.name for rule in RULES}

HTML_COMMENT = re.compile(r'<!--.*?-->', re.DOTALL)
CSS_COMMENT = re.compile(r'/\*.*?\*/', re.DOTALL)
XMLNS = re.compile(r'\sxmlns(?::\w+)?\s*=\s*"[^"]*"')
URL_IGNORED_CHARS = re.compile(r'[\t\n\r]')
_JINJA_IGNORED_TOKENS = {'comment_begin', 'comment', 'comment_end', 'linecomment_begin', 'linecomment', 'linecomment_end', 'whitespace'}
_JINJA_TAG_BEGIN = {'variable_begin', 'block_begin'}


@dataclass(frozen=True)
class ScanTarget:
    """一個檔案依分類準備好的掃描片段。"""

    jinja: tuple[str, ...] = ()
    markup: tuple[str, ...] = ()
    url: tuple[str, ...] = ()
    css: tuple[str, ...] = ()

    def parts(self, category: Category) -> tuple[str, ...]:
        return {'jinja': self.jinja, 'markup': self.markup, 'url': self.url, 'css': self.css}[category]


def url_parts(*texts: str) -> tuple[str, ...]:
    """entity 解碼後的版本，與再移除 `\\t\\n\\r` 的版本。"""
    decoded = [html.unescape(text) for text in texts]
    return (*decoded, *(URL_IGNORED_CHARS.sub('', text) for text in decoded))


def jinja_target(source: str) -> ScanTarget:
    """以 Jinja2 lexer 分開 markup 與 Jinja 程式碼（見模組 docstring）。"""
    spaced: list[str] = []
    joined: list[str] = []
    code: list[str] = []
    for _lineno, token_type, value in templates.env.lex(source):
        if token_type == 'data':
            spaced.append(value)
            joined.append(value)
        elif token_type in _JINJA_IGNORED_TOKENS:
            continue
        else:
            if token_type in _JINJA_TAG_BEGIN:
                spaced.append(' ')
            code.append(value)
    markup = (HTML_COMMENT.sub('', ''.join(spaced)), HTML_COMMENT.sub('', ''.join(joined)))
    return ScanTarget(jinja=(' '.join(code),), markup=markup, url=url_parts(*markup))


def target_for(text: str, suffix: str, *, is_template: bool) -> ScanTarget:
    if is_template:
        return jinja_target(text)
    if suffix == '.css':
        stripped = CSS_COMMENT.sub('', text)
        return ScanTarget(markup=(stripped,), url=(stripped, URL_IGNORED_CHARS.sub('', stripped)), css=(stripped,))
    if suffix == '.svg':
        stripped = XMLNS.sub('', HTML_COMMENT.sub('', text))
        return ScanTarget(markup=(stripped,), url=url_parts(stripped))
    return ScanTarget(markup=(text,), url=url_parts(text))


def violations(text: str, suffix: str = '.html', *, is_template: bool = True) -> list[str]:
    """回傳違反的規則名稱。"""
    target = target_for(text, suffix, is_template=is_template)
    return [rule.name for rule in RULES if any(rule.pattern.search(part) for part in target.parts(rule.category))]


def read_text_or_fail(path: Path) -> str:
    """讀取 UTF-8 文字檔；二進位檔（無法解碼或含 NUL）以明確訊息失敗。"""
    data = path.read_bytes()
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        pytest.fail(f'{path.name} 不是 UTF-8 文字檔，CSP 靜態掃描無法檢查；請改用文字格式或調整本檢查')
    if '\x00' in text:
        pytest.fail(f'{path.name} 含 NUL 字元（疑似二進位檔），CSP 靜態掃描無法檢查')
    return text


def template_files() -> list[Path]:
    return sorted(p for p in TEMPLATES_DIR.rglob('*') if p.is_file())


def static_files() -> list[Path]:
    return sorted(p for p in STATIC_DIR.rglob('*') if p.is_file())


def file_id(path: Path) -> str:
    return path.as_posix().rsplit('/app/', 1)[-1]


# ---------- 實際檔案 ----------


def test_scanned_files_cover_expected_assets() -> None:
    names = {file_id(p) for p in template_files() + static_files()}
    expected = {'templates/base.html', 'templates/macros/forms.html', 'templates/errors/_layout.html', 'static/css/main.css'}
    expected |= {f'templates/errors/{code}.html' for code in (400, 403, 404, 413, 422, 500, 503)}
    assert expected <= names
    assert 'templates/errors/415.html' not in names


@pytest.mark.parametrize('path', template_files(), ids=file_id)
def test_templates_have_no_csp_violations(path: Path) -> None:
    found = violations(read_text_or_fail(path), path.suffix, is_template=True)
    assert found == [], f'{file_id(path)} 含有 CSP 禁止的寫法：{found}'


@pytest.mark.parametrize('path', static_files(), ids=file_id)
def test_static_files_have_no_csp_violations(path: Path) -> None:
    found = violations(read_text_or_fail(path), path.suffix, is_template=False)
    assert found == [], f'{file_id(path)} 含有 CSP 禁止的寫法：{found}'


@pytest.mark.parametrize('path', template_files(), ids=file_id)
def test_forms_use_post_or_get(path: Path) -> None:
    markup = jinja_target(read_text_or_fail(path)).markup[0]
    for form in re.findall(r'<form\b[^>]*>', markup, re.IGNORECASE):
        assert re.search(r'method="(post|get)"', form), form


# ---------- 掃描規則本身的負面測試 ----------


VIOLATION_CASES: list[tuple[str, str, bool, str]] = [
    # jinja
    ('{{ value|safe }}', '.html', True, '|safe'),
    ('{{ value | safe }}', '.html', True, '|safe'),
    ('{% filter safe %}{{ x }}{% endfilter %}', '.html', True, '|safe'),
    ('{{ Markup(value) }}', '.html', True, 'Markup'),
    ('{% autoescape false %}{{ x }}{% endautoescape %}', '.html', True, 'autoescape 區塊'),
    ('{% autoescape 0 %}{{ x }}{% endautoescape %}', '.html', True, 'autoescape 區塊'),
    ('{% autoescape none %}{{ x }}{% endautoescape %}', '.html', True, 'autoescape 區塊'),
    ('{% autoescape not true %}{{ x }}{% endautoescape %}', '.html', True, 'autoescape 區塊'),
    ('{% autoescape true %}{{ x }}{% endautoescape %}', '.html', True, 'autoescape 區塊'),
    ("{{ {'onclick':'x()'}|xmlattr }}", '.html', True, 'xmlattr'),
    ('<p{{ attrs|xmlattr }}>', '.html', True, 'xmlattr'),
    ('{{ value.__html__() }}', '.html', True, '__html__'),
    # markup：標籤與屬性
    ('<script src="/static/a.js"></script>', '.html', True, '<script'),
    ('<style>p{}</style>', '.html', True, '<style'),
    ('<p style="color:red">x</p>', '.html', True, 'style= 屬性'),
    ('<p class="a"style="color:red">x</p>', '.html', True, 'style= 屬性'),
    ('<a href="/" onclick="x()">x</a>', '.html', True, 'on*= 事件屬性'),
    ('<svg/onload=alert(1)>', '.html', True, 'on*= 事件屬性'),
    ('<a href="/"onclick="x()">x</a>', '.html', True, 'on*= 事件屬性'),
    ('<a href="{{ url }}"onclick="x()">x</a>', '.html', True, 'on*= 事件屬性'),
    ('<meta http-equiv="refresh" content="0;url=/x">', '.html', True, 'meta refresh'),
    ("<meta content='0' http-equiv=Refresh>", '.html', True, 'meta refresh'),
    ('<iframe src="/x"></iframe>', '.html', True, '<iframe'),
    ('<div srcdoc="x"></div>', '.html', True, 'srcdoc'),
    ('<base href="/">', '.html', True, '<base'),
    ('<object data="/x"></object>', '.html', True, '<object'),
    ('<embed src="/x">', '.html', True, '<embed'),
    ('<form method="post" enctype="multipart/form-data">', '.html', True, 'enctype'),
    ('@import url(/static/css/other.css);', '.css', False, '@import'),
    ('<a href="&#106;avascript:alert(1)">x</a>', '.html', True, 'URL 屬性含 HTML entity'),
    ('<a href="java&#x09;script:alert(1)">x</a>', '.html', True, 'URL 屬性含 HTML entity'),
    ('<a href="java&Tab;script:alert(1)">x</a>', '.html', True, 'URL 屬性含 HTML entity'),
    # markup：以空的 Jinja 標籤切開關鍵字（N-C）
    ('<scr{% if true %}{% endif %}ipt>alert(1)</script>', '.html', True, '<script'),
    ('<a href="/" on{{ "" }}click="x()">x</a>', '.html', True, 'on*= 事件屬性'),
    ('<p sty{{ \'\' }}le="color:red">x</p>', '.html', True, 'style= 屬性'),
    # markup：註解的處理
    ('<p>/*</p><script>x</script><p>*/</p>', '.html', True, '<script'),
    ('<input accept="image/*"><script>x</script><p>*/</p>', '.html', True, '<script'),
    ("{{ '<!--' }}<script>alert(1)</script>{{ '-->' }}", '.html', True, '<script'),
    ('<!-- @import url(/x.css); -->', '.css', False, '@import'),
    ('<svg>/*<script>x</script>*/</svg>', '.svg', False, '<script'),
    ('<svg onload="x()"></svg>', '.svg', False, 'on*= 事件屬性'),
    # url
    ('<a href="javascript:alert(1)">x</a>', '.html', True, 'javascript: URL'),
    ('<a href="&#106;avascript:alert(1)">x</a>', '.html', True, 'javascript: URL'),
    ('<a href="&#x6A;avascript:alert(1)">x</a>', '.html', True, 'javascript: URL'),
    ('<a href="java&Tab;script:alert(1)">x</a>', '.html', True, 'javascript: URL'),
    ('<a href="java&#x0A;script:alert(1)">x</a>', '.html', True, 'javascript: URL'),
    ('<a href="java\tscript:alert(1)">x</a>', '.html', True, 'javascript: URL'),
    ('<a href="java\nscript:alert(1)">x</a>', '.html', True, 'javascript: URL'),
    ('<img src="data:image/png;base64,AA">', '.html', True, 'data: URI'),
    ('.a { background: url(data:image/png;base64,AA); }', '.css', False, 'data: URI'),
    ('<link rel="stylesheet" href="https://cdn.example.com/x.css">', '.html', True, '外部資源 URL'),
    ('<img src="https://evil.example/x.png">', '.html', True, '外部資源 URL'),
    ('<img src="https:evil.example/x.png">', '.html', True, '外部資源 URL'),
    ('<img src="http:x.png">', '.html', True, '外部資源 URL'),
    ("<img src='//evil.example/x.png'>", '.html', True, '外部資源 URL'),
    ('<img src="/\\evil.example/x.png">', '.html', True, '外部資源 URL'),
    ('<img src="\\\\evil.example/x.png">', '.html', True, '外部資源 URL'),
    ('<img src="&#47;&#47;evil.example/x.png">', '.html', True, '外部資源 URL'),
    ('<img srcset="/a.png 1x, //evil.example/b.png 2x">', '.html', True, '外部資源 URL'),
    ('<video poster="https://evil.example/x.png"></video>', '.html', True, '外部資源 URL'),
    ('<form action=//evil.example method="post">', '.html', True, '外部資源 URL'),
    ('<form method="post" action="https://evil.example/x">', '.html', True, '外部資源 URL'),
    ('<button formaction="//evil.example/x">x</button>', '.html', True, '外部資源 URL'),
    ('<svg><image href="https://evil.example/x.png"/></svg>', '.svg', False, '外部資源 URL'),
    ('<svg><use xlink:href="//evil.example/x.svg#a"/></svg>', '.svg', False, '外部資源 URL'),
    ('.a { background: url(//evil.example/x.png); }', '.css', False, '外部資源 URL'),
    ('.a { background: url( "https://evil.example/x.png"); }', '.css', False, '外部資源 URL'),
    ('.a { background: url(/\\evil.example/x.png); }', '.css', False, '外部資源 URL'),
    ('<a href="//evil.example/x">x</a>', '.html', True, 'href 協定相對 / 反斜線'),
    ('<a href="/\\evil.example/x">x</a>', '.html', True, 'href 協定相對 / 反斜線'),
    ('<a href="\\\\evil.example/x">x</a>', '.html', True, 'href 協定相對 / 反斜線'),
    ('<a href=" //evil.example/x">x</a>', '.html', True, 'href 協定相對 / 反斜線'),
    # css
    ('.a::before { content: "\\3c script"; }', '.css', False, 'CSS 反斜線 escape'),
    ('.a { background: u\\72l(/x.png); }', '.css', False, 'CSS 反斜線 escape'),
]
"""(片段, 副檔名, 是否為 Jinja 樣板, 應命中的規則)。"""


@pytest.mark.parametrize(('snippet', 'suffix', 'is_template', 'rule'), VIOLATION_CASES)
def test_scanner_detects_violations(snippet: str, suffix: str, is_template: bool, rule: str) -> None:
    assert rule in violations(snippet, suffix, is_template=is_template)


ALLOWED_CASES: list[tuple[str, str, bool]] = [
    # 各語法的註解
    ('{# <script> |safe Markup autoescape #}<!-- <style> style= data: -->', '.html', True),
    ('/* <script> data: @import https://x \\3c */ .a { color: red; }', '.css', False),
    ('<svg xmlns="http://www.w3.org/2000/svg"><!-- <script> --></svg>', '.svg', False),
    # Jinja 變數名稱（M-1）
    ('{% set one_day = 1 %}{{ one_day }}', '.html', True),
    ('{% if only_staff == true %}x{% endif %}', '.html', True),
    ('{% for s in slots if s.ongoing == false %}{{ s.name }}{% endfor %}', '.html', True),
    ("{% set style = 'x' %}{{ style }}", '.html', True),
    ('{{ online_count }}{% set onset = 1 %}', '.html', True),
    ("{% set safe_text = 'x' %}{{ safe_text }}{{ markup_preview }}", '.html', True),
    # 已跳脫的文字（m-1）
    ('<p>請勿輸入 &lt;script&gt; 或 &lt;style&gt;</p>', '.html', True),
    ('<p>&lt;iframe&gt;、&lt;object&gt;、&lt;base href=&quot;/&quot;&gt;</p>', '.html', True),
    # 外部連結（n-1）與站內連結
    ('<a href="https://www.tku.edu.tw/">淡江大學</a>', '.html', True),
    ('<a class="button" href="https://www.tku.edu.tw/" rel="noopener">x</a>', '.html', True),
    ('<a href="/venues/{{ v.id }}">{{ v.name }}</a>', '.html', True),
    ('<a href="/venues/{{ v.id }}/availability?week_start={{ week_start }}">x</a>', '.html', True),
    ('<a href="/x?a=1&amp;b=2">x</a><a href="#main">跳到主要內容</a>', '.html', True),
    ('<a class="site-nav__link" href="{{ href }}" aria-current="page">{{ text }}</a>', '.html', True),
    # 一般表單與欄位（T-010～T-020）
    ('<input accept="image/*" aria-describedby="x" data-x="1" class="option">', '.html', True),
    ('<form method="post" action="/bookings">{{ forms.csrf_field() }}</form>', '.html', True),
    ('<form method="get" action="/venues/{{ venue.id }}/availability">', '.html', True),
    ('<option value="{{ v }}"{% if v == sel %} selected{% endif %}>{{ label }}</option>', '.html', True),
    ("{{ forms.input('expected_attendees', '人數', type='number', min=1, inputmode='numeric') }}", '.html', True),
    ('<img src="/static/img/favicon.svg" alt=""><link rel="stylesheet" href="/static/css/main.css">', '.html', True),
    ('<time datetime="{{ b.start_at | local_dt }}">{{ b.start_at | local_dt }}</time>', '.html', True),
    ('<p>時間 10:00～12:00，類別：{{ v.category | category_label }}</p>', '.html', True),
    ('<td data-label="日期">{{ d | local_date }}（{{ d | weekday_label }}）</td>', '.html', True),
    ('<p class="flash flash--{{ level }}" role="{{ role }}">{{ message.text }}</p>', '.html', True),
    ('{% set describedby = x %}{% if value is not none %}{% endif %}{% if errors is mapping %}{% endif %}', '.html', True),
    # CSS / SVG
    ('.button--on-dark { color: #fff; } .a { background: url(/static/img/x.svg); }', '.css', False),
    ('.field__control[aria-invalid="true"] { border-color: #b91c1c; }', '.css', False),
    ('<svg viewBox="0 0 32 32"><rect fill="#1e3a8a"/><use href="#icon"/></svg>', '.svg', False),
]
"""合法寫法（含 T-010～T-020 預期會用到的寫法），不得誤判。"""


@pytest.mark.parametrize(('snippet', 'suffix', 'is_template'), ALLOWED_CASES)
def test_scanner_allows_comments_and_safe_markup(snippet: str, suffix: str, is_template: bool) -> None:
    assert violations(snippet, suffix, is_template=is_template) == []


def test_every_rule_has_negative_test() -> None:
    """每條規則都至少有一個負面測試（避免新增規則卻沒驗證它抓得到）。"""
    covered = {rule for *_, rule in VIOLATION_CASES}
    assert covered == RULE_NAMES


def test_rule_names_unique() -> None:
    assert len(RULE_NAMES) == len(RULES)


def test_escaped_text_only_checked_by_url_rules() -> None:
    """解碼後的片段只套用 url 規則：已跳脫的 `&lt;script&gt;` 不違規，但跳脫的 `javascript:` 仍會被抓到。"""
    target = jinja_target('<p>&lt;script&gt;</p><a href="&#106;avascript:x">x</a>')
    assert not any('<script' in part for part in target.markup)
    assert any('<script' in part for part in target.url)
    assert violations('<p>&lt;script&gt;</p><a href="&#106;avascript:x">x</a>') == ['URL 屬性含 HTML entity', 'javascript: URL']


def test_binary_file_fails_clearly(tmp_path: Path) -> None:
    binary = tmp_path / 'logo.png'
    binary.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\xff\xfe')
    with pytest.raises(pytest.fail.Exception, match='不是 UTF-8 文字檔'):
        read_text_or_fail(binary)


def test_nul_file_fails_clearly(tmp_path: Path) -> None:
    binary = tmp_path / 'x.html'
    binary.write_bytes(b'<p>\x00</p>')
    with pytest.raises(pytest.fail.Exception, match='NUL'):
        read_text_or_fail(binary)
