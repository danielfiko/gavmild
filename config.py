import os

def read_secret(secret_name):
    try:
        with open(f"/run/secrets/{secret_name}", "r") as secret_file:
            return secret_file.read().strip()
    except IOError:
        return None


class Config:
    SECRET_KEY = read_secret("flask-secret-key")
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://dba:{read_secret('dba-password')}@gavmild_db:3306/gavmild"
    TELEGRAM_TOKEN = read_secret("telegram-token")



class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True