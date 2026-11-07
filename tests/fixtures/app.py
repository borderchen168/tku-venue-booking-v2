"""App 相關 fixture：以測試設定建立 app 與 TestClient。"""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.clock import get_clock
from app.core.config import Settings
from app.main import create_app
from tests.fixtures.clock import FixedClock


@pytest.fixture
def app(settings: Settings, fixed_clock: FixedClock) -> FastAPI:
    """以測試設定建立的 app；`get_clock` 固定為 `fixed_clock`。"""
    application = create_app(settings)
    application.dependency_overrides[get_clock] = lambda: fixed_clock
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """TestClient（base_url 為 http://testserver，對應 ALLOWED_HOSTS=testserver）。"""
    with TestClient(app) as test_client:
        yield test_client
