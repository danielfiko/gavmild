import os

from app.utils import read_secret


def _safe_read_secret(name: str) -> str | None:
    try:
        return read_secret(name)
    except Exception:
        return None


class Config:
    SECRET_KEY: str | None = _safe_read_secret("flask-secret-key")
    db_host: str | None = os.getenv("DATABASE_HOST")
    db_user: str | None = os.getenv("DATABASE_USERNAME")
    db_password: str | None = _safe_read_secret("dba-password")
    SQLALCHEMY_DATABASE_URI: str = f"mysql+pymysql://{db_user}:{db_password}@{db_host}"
    OPENAI_TOKEN: str | None = _safe_read_secret("openai-token")
    TELEGRAM_ADMIN_ID: str | None = os.getenv("TELEGRAM_ADMIN_ID")


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE: bool = True
    TELEGRAM_BOT_USERNAME: str | None = os.getenv("TELEGRAM_BOT_USERNAME")
    TELEGRAM_TOKEN: str | None = _safe_read_secret("telegram-token")
    CHAT_GROUP_ID: str | None = os.getenv("TELEGRAM_GROUP_ID")
    WEBAUTHN_RP_ID: str = os.getenv("WEBAUTHN_RP_ID", "")
    WEBAUTHN_ORIGIN: str = os.getenv("WEBAUTHN_ORIGIN", "")
    WEBAUTHN_RP_NAME: str = os.getenv("WEBAUTHN_RP_NAME", "")


class DevelopmentConfig(Config):
    DEBUG = True
    WEBAUTHN_RP_ID = os.getenv("WEBAUTHN_RP_ID_DEV", "")
    WEBAUTHN_ORIGIN = os.getenv("WEBAUTHN_ORIGIN_DEV", "")
    WEBAUTHN_RP_NAME = os.getenv("WEBAUTHN_RP_NAME_DEV", "")
    TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME_DEV")
    CHAT_GROUP_ID = os.getenv("TELEGRAM_GROUP_ID_DEV")
    TELEGRAM_TOKEN: str | None = _safe_read_secret("nei-bot-token")


class TestingConfig(Config):
    TESTING: bool = True
    SECRET_KEY: str = "test-secret-key"
    SQLALCHEMY_DATABASE_URI: str = "sqlite://"
    WTF_CSRF_ENABLED: bool = False
    SERVER_NAME: str = "localhost"
    BCRYPT_LOG_ROUNDS: int = 4


# TODO: ProductionConfig, DevelopmentConfig, and TestingConfig are defined but never used.
#   The app always loads Config via 'app.config.Config'. Wire up environment-based config selection in create_app().
