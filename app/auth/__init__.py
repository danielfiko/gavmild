import os

from flask import Blueprint

APP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(APP_PATH, 'templates/auth')


auth_bp = Blueprint('auth', __name__, template_folder=TEMPLATE_PATH)

from app.auth import controllers  # noqa: E402, F401
from app.auth import decorators  # noqa: E402, F401
from app.auth import models  # noqa: E402, F401
from app.auth import routes  # noqa: E402, F401