"""App 骨架整合測試：/healthz、文件端點關閉、static 掛載、設定注入。"""

import importlib
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app import main as main_module
from app.core.clock import Clock, get_clock
from app.core.config import Settings, get_settings
from app.main import create_app
from tests.fixtures.clock import FixedClock
from tests.fixtures.settings import make_settings


def test_healthz(client: TestClient) -> None:
    response = client.get('/healthz')
    assert response.status_code == 200
    assert response.text == 'ok'
    assert response.headers['content-type'].startswith('text/plain')


@pytest.mark.parametrize('path', ['/docs', '/redoc', '/openapi.json', '/docs/oauth2-redirect', '/api/venues'])
def test_docs_disabled(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 404


def test_app_has_no_openapi(app: FastAPI) -> None:
    assert app.openapi_url is None
    assert app.docs_url is None
    assert app.redoc_url is None


def test_static_mounted(client: TestClient) -> None:
    assert client.get('/static/does-not-exist.css').status_code == 404


def test_static_missing_directory_does_not_break_startup(monkeypatch: pytest.MonkeyPatch, settings: Settings, tmp_path: Path) -> None:
    monkeypatch.setattr(main_module, 'STATIC_DIR', tmp_path / 'missing-static')
    app = create_app(settings)
    with TestClient(app) as test_client:
        assert test_client.get('/healthz').status_code == 200


def test_settings_injected(app: FastAPI, settings: Settings) -> None:
    assert app.state.settings is settings

    @app.get('/_test/settings')
    def read_env(current: Settings = Depends(get_settings)) -> dict[str, str]:
        return {'env': current.APP_ENV, 'db': current.DATABASE_URL}

    with TestClient(app) as test_client:
        body = test_client.get('/_test/settings').json()
    assert body == {'env': 'test', 'db': settings.DATABASE_URL}


def test_clock_override(app: FastAPI, fixed_clock: FixedClock) -> None:
    @app.get('/_test/today')
    def today(clock: Clock = Depends(get_clock)) -> dict[str, str]:
        return {'today': clock.today_local().isoformat()}

    with TestClient(app) as test_client:
        assert test_client.get('/_test/today').json() == {'today': '2026-11-09'}


def test_default_clock_dependency(settings: Settings) -> None:
    app = create_app(settings)

    @app.get('/_test/now')
    def now(clock: Clock = Depends(get_clock)) -> dict[str, bool]:
        return {'aware': clock.now_utc().tzinfo is not None}

    with TestClient(app) as test_client:
        assert test_client.get('/_test/now').json() == {'aware': True}


def test_create_app_without_settings_uses_get_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv('SECRET_KEY', 'env-secret')
    monkeypatch.setenv('APP_ENV', 'test')
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{(tmp_path / "x.db").as_posix()}')
    app = create_app()
    assert app.state.settings is get_settings()
    assert app.state.settings.APP_ENV == 'test'


def test_create_app_fails_on_insecure_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('SECRET_KEY', 'change-me')
    monkeypatch.setenv('APP_ENV', 'production')
    with pytest.raises(ValueError, match='正式環境設定不安全'):
        create_app()


def test_module_app_is_lazy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('SECRET_KEY', 'env-secret')
    module = importlib.reload(main_module)
    try:
        first = module.app
        assert isinstance(first, FastAPI)
        assert module.app is first
        with pytest.raises(AttributeError):
            _ = module.not_exists
    finally:
        importlib.reload(main_module)


def test_app_debug_is_never_passed_to_fastapi(tmp_path: Path) -> None:
    assert create_app(make_settings(tmp_path, APP_DEBUG=True)).debug is False
