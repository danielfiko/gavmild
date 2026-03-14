import os

from flask import Blueprint

APP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(APP_PATH, 'templates/auth')


auth_bp = Blueprint('auth', __name__, template_folder=TEMPLATE_PATH)

from app.auth import controllers
from app.auth import decorators
from app.auth import models
from app.auth import routes