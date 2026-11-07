"""FastAPI 應用程式建立（overview.md 3.2）。

啟動：`python -m uvicorn app.main:app --no-server-header`（`--no-server-header` 為必要參數，overview.md 第 7 節）。
`app` 於第一次存取時才建立（PEP 562 模組 `__getattr__`），因此匯入 `create_app` 不會讀取 `.env`。
"""

from functools import cache
from pathlib import Path
from typing import Final

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging

STATIC_DIR: Final = Path(__file__).resolve().parent / 'static'


def healthz() -> PlainTextResponse:
    """健康檢查：`200 text/plain` `ok`；不輸出版本或 DB 細節（routes.md 2.1）。"""
    return PlainTextResponse('ok')


def create_app(settings: Settings | None = None) -> FastAPI:
    """建立 FastAPI app；`settings` 省略時使用 `get_settings()`（讀取 `.env`）。

    設定的注入方式（後續 Task 必須遵守，否則測試會讀到開發機的 `.env`）：

    - route / 相依只透過 `Depends(get_settings)` 取得設定；本函式以 `app.dependency_overrides[get_settings]`
      把傳入的 `settings` 注入（測試時即為 tmp_path 的測試設定）。
    - middleware、DB engine 等在建立 app 時就需要設定的元件，必須從本函式的 `settings`（或 `app.state.settings`）
      經建構子傳入；**不得**在模組層級或 import 時呼叫 `get_settings()`。
    - 測試不得呼叫 `app.dependency_overrides.clear()`（會移除設定注入）；只移除自己加入的鍵。
    """
    settings = settings if settings is not None else get_settings()
    configure_logging(settings)

    # 關閉自動文件與 OpenAPI schema（overview.md 第 1 節）。
    # APP_DEBUG 不傳給 FastAPI：Starlette debug 模式會略過自訂的 500 handler（T-023）。
    app = FastAPI(title='淡江場地預約系統', docs_url=None, redoc_url=None, openapi_url=None)
    # T-023：第一步設定 app.router.route_class = LimitedFormRoute（須在註冊任何 route 之前）。

    app.state.settings = settings
    app.dependency_overrides[get_settings] = lambda: settings

    # T-023：middleware 掛載（外→內 SecurityHeaders → RequestId → TrustedHost → BodySizeLimit → FormContentType
    #        →（ServerSession，T-007）），add_middleware 後加者在外層，須以相反順序加入。
    # T-023：register_exception_handlers(app)
    # T-007：csrf_protect 全域相依

    app.add_api_route('/healthz', healthz, methods=['GET'], response_class=PlainTextResponse, include_in_schema=False)
    # check_dir=False：靜態檔目錄不存在時仍可啟動（請求時才檢查）
    app.mount('/static', StaticFiles(directory=STATIC_DIR, check_dir=False), name='static')

    # T-023：for router in ALL_ROUTERS: app.include_router(router)（只從 app/routers/__init__.py 的清單掛載）
    return app


@cache
def _default_app() -> FastAPI:
    return create_app()


def __getattr__(name: str) -> FastAPI:
    """延遲建立 `app.main:app`（供 Uvicorn 使用）。"""
    if name == 'app':
        return _default_app()
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
