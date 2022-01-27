from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object("config.ProductionConfig")
print(app.config['SQLALCHEMY_DATABASE_URI'])
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

from .models import User


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


from app.blueprints.api.api import api_bp
from .blueprints.auth.auth import auth_bp
from .blueprints.views.views import views_bp
from app.blueprints.views.wishes import wishes_bp

app.register_blueprint(api_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(views_bp)
app.register_blueprint(wishes_bp)

db.create_all()
