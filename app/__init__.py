import os
from flask import Flask
from threading import Thread


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object('config.Config')

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
