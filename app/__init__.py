import os
from flask import Flask
from .database import database
from .blueprints.auth import views as auth
# blueprint import
from .blueprints.auth.views import auth_bp
from .blueprints.wishlist.views import wishlist_bp
from app.blueprints.wishlist.api import api_bp

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object('config.Config')

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!!!444'

    app.register_blueprint(auth_bp)
    app.register_blueprint(wishlist_bp)
    app.register_blueprint(api_bp)

    # from . import blog
    # app.register_blueprint(blog.bp)
    # app.add_url_rule("/", endpoint="index")


    database.init_app(app)
    auth.init_auth(app)
    
    return app
