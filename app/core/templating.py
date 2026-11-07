"""Jinja2 環境、context processor 與顯示用 filter（routes.md 第 3 節、overview.md 第 5 節）。

- autoescape 一律開啟（AGENTS.md 2.3 XSS）。
- context processor 一律以 `getattr(request.state, ..., None)` 取值：500 handler 在 Session 載入前執行時，
  `request.state` 可能沒有 `session` / `current_user`，此時視為未登入（error-handling.md 3.2）。
  實際值由 T-007（`session`、`messages`）與 T-008（`current_user`）填入。
- 列舉中文標籤集中在本模組，樣板不得自行寫死對照（overview.md 第 5 節）。
- 時間 filter（`local_dt`、`local_date`、`hhmm`）從渲染 context 的 `app_timezone` 取得時區。Jinja2 的
  `{% import %}` 預設**不帶** context，因此在 macro 中使用這些 filter 時，必須以
  `{% import 'macros/forms.html' as forms with context %}` 匯入；否則 filter 取不到 `app_timezone`，
  會改用預設時區 `Asia/Taipei`（與 `APP_TIMEZONE` 不同時顯示會錯）。
"""

import datetime as dt
from pathlib import Path
from typing import Any, Final
from zoneinfo import ZoneInfo

import jinja2
from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.core.config import DEFAULT_APP_TIMEZONE, Settings
from app.core.timeutils import utc_to_local

TEMPLATES_DIR: Final = Path(__file__).resolve().parent.parent / 'templates'

STATUS_LABELS: Final[dict[str, str]] = {
    'pending': '審核中',
    'approved': '已核准',
    'rejected': '已駁回',
    'cancelled': '已取消',
}
REASON_TYPE_LABELS: Final[dict[str, str]] = {
    'national_holiday': '國定假日',
    'exam_week': '考試週',
    'major_exam': '大型考試',
    'other': '其他',
}
CATEGORY_LABELS: Final[dict[str, str]] = {
    'club_activity': '社團活動場地',
    'stall': '擺攤場地',
}
WEEKDAY_LABELS: Final[tuple[str, ...]] = ('一', '二', '三', '四', '五', '六', '日')


def _settings_of(request: Request) -> Settings | None:
    """取得 `create_app` 存放在 `app.state.settings` 的設定；不在 app 內（單元測試）時回傳 None。"""
    app = request.scope.get('app')
    if app is None:
        return None
    settings = getattr(app.state, 'settings', None)
    return settings if isinstance(settings, Settings) else None


def _csrf_token_of(request: Request, session: object | None) -> str | None:
    """已登入：Session 的 Token；未登入（/login 頁）：route 放在 `request.state.login_csrf_token` 的登入前 Token（ADR-002）。"""
    if session is not None:
        session_token = getattr(session, 'csrf_token', None)
        return session_token if isinstance(session_token, str) else None
    login_token = getattr(request.state, 'login_csrf_token', None)
    return login_token if isinstance(login_token, str) else None


def app_context(request: Request) -> dict[str, Any]:
    """所有樣板共用的 context（routes.md 第 3 節）。缺少 `current_user` / `session` 時視為未登入。"""
    current_user = getattr(request.state, 'current_user', None)
    session = getattr(request.state, 'session', None)
    csrf_token = _csrf_token_of(request, session)
    settings = _settings_of(request)
    return {
        'current_user': current_user,
        'csrf_token': csrf_token,
        # T-007 以 pop_flashes 填入（已登入時讀取後即從 Session 移除）；未登入為空 list
        'messages': [],
        'app_timezone': settings.APP_TIMEZONE if settings is not None else DEFAULT_APP_TIMEZONE,
    }


def _tz_from(context: jinja2.runtime.Context) -> ZoneInfo:
    name = context.get('app_timezone')
    return ZoneInfo(name if isinstance(name, str) else DEFAULT_APP_TIMEZONE)


@jinja2.pass_context
def local_dt(context: jinja2.runtime.Context, value: dt.datetime | None) -> str:
    """UTC aware datetime → `APP_TIMEZONE` 的 `YYYY-MM-DD HH:MM`；None 輸出空字串。"""
    if value is None:
        return ''
    return utc_to_local(value, _tz_from(context)).strftime('%Y-%m-%d %H:%M')


@jinja2.pass_context
def local_date(context: jinja2.runtime.Context, value: dt.datetime | dt.date | None) -> str:
    """`YYYY-MM-DD`；datetime 先轉為 `APP_TIMEZONE`，date（已是當地日曆日）直接輸出。"""
    if value is None:
        return ''
    if isinstance(value, dt.datetime):
        value = utc_to_local(value, _tz_from(context)).date()
    return value.isoformat()


@jinja2.pass_context
def hhmm(context: jinja2.runtime.Context, value: dt.datetime | dt.time | None) -> str:
    """`HH:MM`；datetime 先轉為 `APP_TIMEZONE`，time（當地時刻）直接輸出。"""
    if value is None:
        return ''
    if isinstance(value, dt.datetime):
        value = utc_to_local(value, _tz_from(context)).time()
    return value.strftime('%H:%M')


def _label(labels: dict[str, str], value: object) -> str:
    text = '' if value is None else str(value)
    return labels.get(text, text)


def status_label(value: object) -> str:
    """申請狀態中文標籤（`BookingStatus`）。未知值原樣輸出（仍經 autoescape）。"""
    return _label(STATUS_LABELS, value)


def reason_type_label(value: object) -> str:
    """不開放原因類型中文標籤（`ClosedReasonType`）。"""
    return _label(REASON_TYPE_LABELS, value)


def category_label(value: object) -> str:
    """場地類別中文標籤（`VenueCategory`）。"""
    return _label(CATEGORY_LABELS, value)


def weekday_label(value: dt.date | int) -> str:
    """星期中文（一～日）；接受日期或 `weekday()` 數值（0＝週一）。

    Raises:
        ValueError: 數值不在 0～6（避免負數索引悄悄取到錯誤的星期）。
    """
    index = value if isinstance(value, int) else value.weekday()
    if not 0 <= index < len(WEEKDAY_LABELS):
        raise ValueError('weekday_label 只接受 0～6')
    return WEEKDAY_LABELS[index]


def build_environment(directory: Path = TEMPLATES_DIR) -> jinja2.Environment:
    """建立 autoescape 全開的 Jinja2 環境並註冊 filter。"""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(directory),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters.update(
        {
            'local_dt': local_dt,
            'local_date': local_date,
            'hhmm': hhmm,
            'status_label': status_label,
            'reason_type_label': reason_type_label,
            'category_label': category_label,
            'weekday_label': weekday_label,
        }
    )
    return env


templates: Final = Jinja2Templates(env=build_environment(), context_processors=[app_context])
"""全站共用的樣板渲染器：`templates.TemplateResponse(request, 'home.html', {...})`。"""
