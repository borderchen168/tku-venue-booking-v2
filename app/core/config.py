"""應用程式設定：以 pydantic-settings 讀取 `.env` 與環境變數（overview.md 第 4 節）。

所有設定只能由本模組的 `Settings` 讀取；程式中禁止寫死秘密值或環境相依設定（AGENTS.md 1.2）。
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Final, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

PROJECT_ROOT: Final = Path(__file__).resolve().parent.parent.parent
"""專案根目錄（`DATABASE_URL` 相對路徑與 `.env` 的解析基準）。"""

ENV_FILE: Final = PROJECT_ROOT / '.env'

DEFAULT_APP_TIMEZONE: Final = 'Asia/Taipei'

SQLITE_URL_PREFIX: Final = 'sqlite:///'

SECURE_COOKIE_PREFIX: Final = '__Host-'

MIN_PRODUCTION_SECRET_KEY_LENGTH: Final = 32

MIN_PRODUCTION_SECRET_KEY_DISTINCT_CHARS: Final = 10
"""正式環境 SECRET_KEY 至少要有的不同字元數：擋下 'a' * 32 這類低熵值，且 `secrets.token_hex()`（只有 16 種字元）也能通過。"""

FORBIDDEN_SECRET_KEYS: Final[frozenset[str]] = frozenset(
    {
        'change-me',
        # `.env.example` 的 SECRET_KEY 範例值；範例值變更時須同步（tests/unit/test_config.py 會檢查，ADR-002 4.4）
        'replace-with-output-of-secrets-token-urlsafe-64-do-not-use-this-example-value',
    }
)
"""正式環境禁止使用的 SECRET_KEY（範例值、預設值），ADR-002 4.4。"""

AppEnv = Literal['development', 'test', 'production']
LogLevel = Literal['DEBUG', 'INFO', 'WARNING', 'ERROR']


class Settings(BaseSettings):
    """全部執行期設定；欄位名稱即環境變數名稱（區分大小寫）。

    驗證失敗時拋 `pydantic.ValidationError`，應用程式即啟動失敗。

    記錄驗證錯誤時一律使用 `exc.errors(include_input=False, include_context=False)`（或只記 `loc` 與 `type`）：
    `hide_input_in_errors=True` 只會遮蔽 `str(exc)`，`exc.errors()` 預設仍含原始輸入（可能是 SECRET_KEY）。
    `.env` 只能放本類別的欄位（`extra='forbid'`）；Uvicorn 參數（例如 `FORWARDED_ALLOW_IPS`）請用命令列或另外的環境變數。
    """

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding='utf-8',
        case_sensitive=True,
        # `.env` 中拼錯或不存在的鍵直接啟動失敗（錯誤訊息只含鍵名，不含值）
        extra='forbid',
        frozen=True,
        # 驗證錯誤訊息不得帶出原始輸入（否則 SECRET_KEY 會出現在啟動錯誤日誌中）
        hide_input_in_errors=True,
    )

    APP_ENV: AppEnv = 'development'
    APP_DEBUG: bool = False

    SECRET_KEY: SecretStr = Field(min_length=1)
    """用途：經 `derive_key('login-csrf')` 衍生登入前 CSRF 金鑰（ADR-002 4.4）。"""

    DATABASE_URL: str = 'sqlite:///./data/app.db'
    DATABASE_BUSY_TIMEOUT_MS: int = Field(default=5000, ge=100, le=60000)

    APP_TIMEZONE: str = DEFAULT_APP_TIMEZONE

    ALLOWED_HOSTS: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ['localhost', '127.0.0.1'])
    MAX_REQUEST_BODY_BYTES: int = Field(default=65536, ge=1024, le=1048576)

    SESSION_COOKIE_NAME: str = Field(default='tku_session', min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')
    SESSION_COOKIE_SECURE: bool = False
    SESSION_MAX_AGE_SECONDS: int = Field(default=1800, gt=0)
    SESSION_ABSOLUTE_MAX_AGE_SECONDS: int = Field(default=28800, gt=0)

    LOGIN_CSRF_MAX_AGE_SECONDS: int = Field(default=3600, ge=300, le=86400)
    LOGIN_MAX_ATTEMPTS: int = Field(default=5, ge=1, le=100)
    LOGIN_LOCKOUT_SECONDS: int = Field(default=900, gt=0)

    PASSWORD_HASH_CONCURRENCY: int = Field(default=4, ge=1, le=32)

    LOG_LEVEL: LogLevel = 'INFO'

    @field_validator('APP_TIMEZONE')
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        """時區必須能被 `ZoneInfo` 載入（ADR-004）。"""
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError('APP_TIMEZONE 必須是有效的 IANA 時區名稱') from exc
        return value

    @field_validator('DATABASE_URL')
    @classmethod
    def _validate_database_url(cls, value: str) -> str:
        """只接受 `sqlite:///<檔案路徑>`；相對路徑以專案根目錄解析為絕對路徑。"""
        if not value.startswith(SQLITE_URL_PREFIX):
            raise ValueError('DATABASE_URL 只接受 sqlite:/// 開頭的檔案路徑')
        raw_path = value.removeprefix(SQLITE_URL_PREFIX)
        if not raw_path or raw_path == ':memory:' or '?' in raw_path:
            raise ValueError('DATABASE_URL 必須指向 SQLite 檔案路徑，且不得帶查詢參數')
        path = Path(raw_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return SQLITE_URL_PREFIX + path.resolve().as_posix()

    @field_validator('ALLOWED_HOSTS', mode='before')
    @classmethod
    def _split_allowed_hosts(cls, value: object) -> object:
        """環境變數以逗號分隔；去除空白與空項目。"""
        if isinstance(value, str):
            return [host.strip() for host in value.split(',') if host.strip()]
        if isinstance(value, list | tuple):
            return [str(host).strip() for host in value if str(host).strip()]
        return value

    @model_validator(mode='after')
    def _validate_cross_fields(self) -> Settings:
        """跨欄位與正式環境的啟動檢查（overview.md 第 4 節、ADR-002 4.4 / 4.5）。

        錯誤訊息只描述規則，不包含 SECRET_KEY 等設定值。
        """
        if self.SESSION_ABSOLUTE_MAX_AGE_SECONDS < self.SESSION_MAX_AGE_SECONDS:
            raise ValueError('SESSION_ABSOLUTE_MAX_AGE_SECONDS 必須大於或等於 SESSION_MAX_AGE_SECONDS')
        # 不論環境：__Host- Cookie 必須帶 Secure，否則瀏覽器會拒絕（ADR-002 4.5）
        if self.SESSION_COOKIE_NAME.startswith(SECURE_COOKIE_PREFIX) and not self.SESSION_COOKIE_SECURE:
            raise ValueError('SESSION_COOKIE_NAME 以 __Host- 開頭時 SESSION_COOKIE_SECURE 必須為 true')
        if self.APP_ENV == 'production':
            self._validate_production()
        return self

    def _validate_production(self) -> None:
        """正式環境的額外限制；任何一項不符即啟動失敗。"""
        problems: list[str] = []
        if self.APP_DEBUG:
            problems.append('APP_DEBUG 必須為 false')
        secret = self.SECRET_KEY.get_secret_value()
        if (
            len(secret) < MIN_PRODUCTION_SECRET_KEY_LENGTH
            or secret in FORBIDDEN_SECRET_KEYS
            or secret.strip() != secret
            or len(set(secret)) < MIN_PRODUCTION_SECRET_KEY_DISTINCT_CHARS
        ):
            problems.append('SECRET_KEY 必須是至少 32 字元的高強度亂數（前後不可有空白、至少 10 種不同字元），且不得使用範例值')
        if not self.SESSION_COOKIE_NAME.startswith(SECURE_COOKIE_PREFIX):
            problems.append('SESSION_COOKIE_NAME 必須以 __Host- 開頭')
        if not self.SESSION_COOKIE_SECURE:
            problems.append('SESSION_COOKIE_SECURE 必須為 true')
        # 只能填完整主機名稱：拒絕 '*' 與 '*.example.edu' 等任何含萬用字元的項目
        if not self.ALLOWED_HOSTS or any('*' in host for host in self.ALLOWED_HOSTS):
            problems.append('ALLOWED_HOSTS 不可為空，且只能填完整主機名稱（不可含 *）')
        if problems:
            raise ValueError('正式環境設定不安全：' + '；'.join(problems))

    @property
    def tz(self) -> ZoneInfo:
        """`APP_TIMEZONE` 對應的 `ZoneInfo`（顯示與規則判斷共用，ADR-004）。"""
        return ZoneInfo(self.APP_TIMEZONE)

    @property
    def database_path(self) -> Path:
        """`DATABASE_URL` 指向的 SQLite 檔案絕對路徑。"""
        return Path(self.DATABASE_URL.removeprefix(SQLITE_URL_PREFIX))

    @property
    def is_production(self) -> bool:
        """是否為正式環境。"""
        return self.APP_ENV == 'production'


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """取得全域設定（快取）；FastAPI 以 `Depends(get_settings)` 注入，測試以 `dependency_overrides` 或 `create_app(settings)` 替換。"""
    return Settings()
