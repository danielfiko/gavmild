import os

def read_secret(secret_name): #TODO: Duplikat implementasjon
    try:
        with open(f"/run/secrets/{secret_name}", "r") as secret_file:
            return secret_file.read().strip()
    except IOError:
        return None


class Config:
    SECRET_KEY = read_secret("flask-secret-key")
    db_host = os.getenv("DATABASE_HOST")
    dba_password = read_secret('dba-password')
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://dba:{dba_password}@{db_host}"
    TELEGRAM_TOKEN = read_secret("telegram-token")
    BOT_API_TOKEN = read_secret("bot-api-token")


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True