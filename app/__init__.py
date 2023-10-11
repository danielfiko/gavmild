import os
from flask import Flask, abort
from flask_login import current_user
from flask_wtf.csrf import CSRFProtect
from threading import Thread
from functools import wraps


csrf = CSRFProtect()

def create_app():
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object('config.Config')
    csrf.init_app(app)

    from app.database.database import db
    db.init_app(app)

    # Blueprint import
    from app.auth.controllers import auth_bp
    from app.wishlist.controllers import wishlist_bp
    from app.wishlist.api import api_bp
    from app.telegram.controllers import telegram_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(wishlist_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(telegram_bp)


    with app.app_context():
        db.create_all()
    
    from app.auth import controllers as auth
    #from app.telegram.controllers import run_bot
    auth.init_auth(app)
    #Thread(target=run_bot).start()

    return app

def read_secret(secret_name):
    try:
        with open(f"/run/secrets/{secret_name}", "r") as secret_file:
            return secret_file.read().strip()
    except IOError:
        print(f"Secret '{secret_name}' not found.")

def api_login_required(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        return view_function(*args, **kwargs)
    return decorated_function
