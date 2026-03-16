import os

from flask import Blueprint


APP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(APP_PATH, 'templates/webauthn')

webauthn_bp = Blueprint("webauthn", __name__, url_prefix='/webauthn', template_folder=TEMPLATE_PATH)

from app.webauthn import controllers  # noqa: E402, F401
from app.webauthn import models  # noqa: E402, F401