import os

from flask import Blueprint

APP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(APP_PATH, "templates/admin")

admin_bp = Blueprint("admin", __name__, template_folder=TEMPLATE_PATH, url_prefix="/admin")

from app.admin import routes  # noqa: E402, F401
