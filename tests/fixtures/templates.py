"""樣板渲染測試用 helper：以實際的 `app.core.templating.templates`（含 context processor 與 filter）渲染。"""

import re
from html.parser import HTMLParser
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from starlette.requests import Request

from app.core.templating import app_context, templates

ERROR_STATUSES: tuple[int, ...] = (400, 403, 404, 413, 422, 500, 503)
"""T-002 的 7 個錯誤頁（不含 415，error-handling.md 3.2）。"""

DEFAULT_SESSION_CSRF = 'session-csrf-token'
TITLE_SEPARATOR = '\uff5c'
"""頁面標題分隔字元（全形直線 U+FF5C，style-guide.md 第 9 節），以跳脫序列表示避免 RUF001。"""


def make_request(path: str = '/', app: FastAPI | None = None, **state: Any) -> Request:
    """建立 Starlette `Request`；`state` 的鍵值會設到 `request.state`（未給的屬性保持不存在）。

    `app` 省略時 scope 沒有 `app`（context processor 視為不在 app 內，使用預設時區）。
    """
    scope: dict[str, Any] = {
        'type': 'http',
        'method': 'GET',
        'scheme': 'http',
        'server': ('testserver', 80),
        'path': path,
        'raw_path': path.encode('utf-8'),
        'root_path': '',
        'headers': [(b'host', b'testserver')],
        'query_string': b'',
    }
    if app is not None:
        scope['app'] = app
    request = Request(scope)
    for key, value in state.items():
        setattr(request.state, key, value)
    return request


def make_user(role: str, display_name: str = '測試使用者', user_id: int = 1) -> SimpleNamespace:
    """模擬 `CurrentUser`（routes.md 3.1 欄位：id、username、display_name、role、is_staff、is_student）。"""
    return SimpleNamespace(
        id=user_id,
        username=f'{role}01',
        display_name=display_name,
        role=role,
        is_staff=role == 'staff',
        is_student=role == 'student',
    )


def logged_in_state(role: str, csrf: str = DEFAULT_SESSION_CSRF, display_name: str = '測試使用者') -> dict[str, Any]:
    """已登入的 `request.state` 屬性（`current_user` ＋ `csrf_token` 為 `csrf` 的 session）。"""
    return {'current_user': make_user(role, display_name), 'session': SimpleNamespace(csrf_token=csrf)}


def render_file(request: Request, name: str, context: dict[str, Any] | None = None) -> str:
    """以 `templates.TemplateResponse` 渲染檔案樣板，回傳 HTML 字串。"""
    response = templates.TemplateResponse(request, name, context or {})
    return bytes(response.body).decode('utf-8')


def render_source(request: Request, source: str, **context: Any) -> str:
    """以實際的 Jinja2 環境渲染字串樣板，context 合併順序與 `TemplateResponse` 相同（processor 最後覆寫）。"""
    merged: dict[str, Any] = dict(context)
    merged.setdefault('request', request)
    merged.update(app_context(request))
    return templates.env.from_string(source).render(merged)


Attrs = dict[str, str | None]


class _TagCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, Attrs]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))


def find_tags(html: str, tag: str, **expected: str) -> list[Attrs]:
    """解析 HTML，回傳名稱為 `tag` 且屬性符合 `expected` 的開始標籤屬性（不受空白與屬性順序影響）。

    屬性值已解碼 HTML entity；`expected` 的鍵中 `_` 代表 `-`（例如 `aria_invalid`）。
    """
    collector = _TagCollector()
    collector.feed(html)
    collector.close()
    wanted = {key.replace('_', '-'): value for key, value in expected.items()}
    return [attrs for name, attrs in collector.tags if name == tag and all(attrs.get(k) == v for k, v in wanted.items())]


def find_tag(html: str, tag: str, **expected: str) -> Attrs:
    """同 `find_tags`，但必須恰好找到一個。"""
    found = find_tags(html, tag, **expected)
    assert len(found) == 1, f'<{tag} {expected}> 應恰好一個，實際 {len(found)} 個'
    return found[0]


def element_text(html: str, tag: str, **expected: str) -> str:
    """回傳第一個符合條件的元素的文字內容（去除前後空白、合併連續空白；不支援同名巢狀元素）。"""
    attr_pattern = ''.join(rf'(?=[^>]*\s{re.escape(k.replace("_", "-"))}="{re.escape(v)}")' for k, v in expected.items())
    match = re.search(rf'<{tag}\b{attr_pattern}[^>]*>(.*?)</{tag}>', html, re.DOTALL)
    assert match is not None, f'找不到 <{tag} {expected}>'
    text = re.sub(r'<[^>]+>', '', match.group(1))
    return ' '.join(text.split())


GLUED_TAG_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r'</li>[^\n]*<li[\s>]'),
    re.compile(r'</p>[^\n]*<p[\s>]'),
    re.compile(r'</div>[^\n]*<div[\s>]'),
    re.compile(r'</option>[^\n]*<option[\s>]'),
)


def glued_lines(html: str) -> list[str]:
    """回傳「結束標籤後同一行又出現同類開始標籤」的行（style-guide 7.6 空白控制回歸檢查）。"""
    return [line for line in html.splitlines() if any(p.search(line) for p in GLUED_TAG_PATTERNS)]
