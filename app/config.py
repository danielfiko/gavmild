import os

from app.utils import read_secret


class Config:
    SECRET_KEY = read_secret("flask-secret-key")
    db_host = os.getenv("DATABASE_HOST")
    db_user = os.getenv("DATABASE_USERNAME")
    db_password = read_secret('dba-password')
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{db_user}:{db_password}@{db_host}"
    OPENAI_TOKEN = read_secret("openai-token")
    CHAT_GROUP_ID = os.getenv("TELEGRAM_GROUP_ID")
    TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")

class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True
    TELEGRAM_TOKEN = read_secret("telegram-token")
    WEBAUTHN_RP_ID = os.getenv("WEBAUTHN_RP_ID", "")
    WEBAUTHN_ORIGIN = os.getenv("WEBAUTHN_ORIGIN", "")
    WEBAUTHN_RP_NAME = os.getenv("WEBAUTHN_RP_NAME", "")


class DevelopmentConfig(Config):
    DEBUG = True
    TELEGRAM_TOKEN = read_secret("nei-bot-token")
    WEBAUTHN_RP_ID = os.getenv("WEBAUTHN_RP_ID_DEV", "")
    WEBAUTHN_ORIGIN = os.getenv("WEBAUTHN_ORIGIN_DEV", "")
    WEBAUTHN_RP_NAME = os.getenv("WEBAUTHN_RP_NAME_DEV", "")


class TestingConfig(Config):
    TESTING = True

# TODO: ProductionConfig, DevelopmentConfig, and TestingConfig are defined but never used.
#   The app always loads Config via 'app.config.Config'. Wire up environment-based config selection in create_app().
