import atexit
import logging
import os
from functools import wraps

from flask import Flask, abort
from flask_login import current_user, LoginManager
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


def create_app(config_class: type | None = None):
    logging.basicConfig(level=logging.INFO)

    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    if config_class is not None:
        app.config.from_object(config_class)
    else:
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
    from app.wishlist.product_extractor import extractor_bp
    from app.wishlist.api import api_bp
    from app.telegram import telegram_bp
    from app.webauthn import webauthn_bp
    from app.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(wishlist_bp)
    app.register_blueprint(extractor_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(telegram_bp)
    app.register_blueprint(webauthn_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        db.create_all()  # TODO: Replace db.create_all() with Alembic/Flask-Migrate for proper database migrations

        from sqlalchemy import inspect, text

        inspector = inspect(db.engine)

        # Add is_admin column to existing databases that predate this column
        existing_user_columns = [col["name"] for col in inspector.get_columns("user")]
        if "is_admin" not in existing_user_columns:
            with db.engine.connect() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE user ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"
                    )
                )
                conn.commit()

        # Add list_id column to wish table if it does not yet exist
        existing_wish_columns = [col["name"] for col in inspector.get_columns("wish")]
        if "list_id" not in existing_wish_columns:
            with db.engine.connect() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE wish ADD COLUMN list_id INT NULL REFERENCES wish_list(id)"
                    )
                )
                conn.execute(
                    text("CREATE INDEX IF NOT EXISTS ix_wish_list_id ON wish (list_id)")
                )
                conn.commit()

        if "img_broken_since" not in existing_wish_columns:
            with db.engine.connect() as conn:
                conn.execute(
                    text("ALTER TABLE wish ADD COLUMN img_broken_since DATETIME NULL")
                )
                conn.commit()

        # Ensure the first registered user (id=1) has admin access
        from app.auth.models import User as _User

        first_user = db.session.get(_User, 1)
        if first_user is not None and not first_user.is_admin:
            first_user.is_admin = True
            db.session.commit()

        # Create one Inbox WishList per user and backfill un-assigned wishes into it
        from app.auth.models import User as _User2
        from app.wishlist.models import Wish as _Wish, WishList as _WishList
        from app.wishlist.controllers import calculate_expires_at
        from datetime import datetime, timezone as _tz

        all_users = db.session.execute(db.select(_User2)).scalars().all()
        for _u in all_users:
            has_list = db.session.execute(
                db.select(_WishList).where(_WishList.user_id == _u.id).limit(1)
            ).scalar_one_or_none()
            current_year = datetime.now().year
            if has_list is None:
                birthday = _u.date_of_birth.replace(year=current_year, tzinfo=_tz.utc)
                if birthday <= datetime.now(_tz.utc):
                    title = f"Jul {current_year}"
                    expires_at = calculate_expires_at("christmas", _u)
                else:
                    title = f"Bursdag {current_year}"
                    expires_at = birthday
                inbox = _WishList(
                    user_id=_u.id,
                    title=title,
                    template="birthday",
                    expires_at=expires_at,
                )
                db.session.add(inbox)
                db.session.flush()  # get inbox.id before committing
                db.session.execute(
                    db.update(_Wish)
                    .where(_Wish.user_id == _u.id, _Wish.list_id.is_(None))
                    .values(list_id=inbox.id)
                )
        db.session.commit()

    from app.telegram.bot import start_bot

    # Flask's debug reloader spawns two processes; only start the bot in the
    # actual server process (WERKZEUG_RUN_MAIN=true) to avoid two instances
    # polling Telegram at the same time.
    if not app.config.get("TESTING") and (
        os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug
    ):
        start_bot(app)

    # Start the background scheduler that archives expired wish lists.
    # Uses the same debug-reloader guard as the Telegram bot to prevent
    # duplicate scheduler instances when Flask restarts.
    if not app.config.get("TESTING") and (
        os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug
    ):
        from apscheduler.schedulers.background import BackgroundScheduler
        from app.wishlist.jobs import (
            archive_expired_lists,
            generate_missing_wish_images,
        )

        scheduler = BackgroundScheduler()
        scheduler.add_job(archive_expired_lists, "interval", minutes=5, args=[app])
        scheduler.add_job(
            generate_missing_wish_images,
            "interval",
            minutes=1,
            args=[app],
        )
        scheduler.start()
        atexit.register(scheduler.shutdown)

    return app


def api_login_required(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        return view_function(*args, **kwargs)

    return decorated_function
