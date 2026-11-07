"""設定相關 fixture：隔離環境變數與 `.env`，每個測試使用 tmp_path 下的獨立設定。"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from app.core.config import Settings, get_settings

TEST_SECRET_KEY = 'test-secret-key-for-pytest-only-0123456789abcdef'


@pytest.fixture(autouse=True)
def isolate_settings_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """不讀開發機的 `.env` 與環境變數，避免測試結果受開發環境影響。"""
    monkeypatch.setitem(Settings.model_config, 'env_file', None)
    for name in Settings.model_fields:
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def make_settings(tmp_path: Path, **overrides: Any) -> Settings:
    """建立測試用設定（APP_ENV=test、ALLOWED_HOSTS=testserver、SQLite 在 tmp_path 下）；`overrides` 覆寫任意欄位。"""
    values: dict[str, Any] = {
        'APP_ENV': 'test',
        'SECRET_KEY': TEST_SECRET_KEY,
        'DATABASE_URL': f'sqlite:///{(tmp_path / "test.db").as_posix()}',
        'ALLOWED_HOSTS': ['testserver'],
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """測試用設定（每個測試獨立）。"""
    return make_settings(tmp_path)
