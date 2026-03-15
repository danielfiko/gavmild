import os
from functools import wraps

from flask import Flask, abort
from flask_login import current_user,LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

from app.config import ProductionConfig, DevelopmentConfig, TestingConfig

class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
bcrypt = Bcrypt()
csrf = CSRFProtect()


def create_app():
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    config_name = os.getenv("FLASK_ENV", "development")
    config_map = {
        "production": ProductionConfig,
        "development": DevelopmentConfig,
        "testing": TestingConfig,
    }
    app.config.from_object(config_map.get(config_name, DevelopmentConfig))

    login_manager.login_view = "auth.login"
    login_manager.init_app(app)
    csrf.init_app(app)
    bcrypt.init_app(app)
    from app import db
    db.init_app(app)

    # Blueprint import
    from app.auth import auth_bp
    from app.wishlist import wishlist_bp
    from app.wishlist.api import api_bp
    from app.telegram import telegram_bp
    from app.webauthn import webauthn_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(wishlist_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(telegram_bp)
    app.register_blueprint(webauthn_bp)

    with app.app_context():
        db.create_all()  # TODO: Replace db.create_all() with Alembic/Flask-Migrate for proper database migrations

    from app.telegram.bot import start_bot
    # Flask's debug reloader spawns two processes; only start the bot in the
    # actual server process (WERKZEUG_RUN_MAIN=true) to avoid two instances
    # polling Telegram at the same time.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        start_bot(app)

    return app

def api_login_required(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        return view_function(*args, **kwargs)
    return decorated_function
