import os

from flask import Blueprint

APP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(APP_PATH, 'templates/wishlist')

wishlist_bp = Blueprint('wishlist', __name__, template_folder=TEMPLATE_PATH,
                        url_prefix='/')  # static_folder='static/views'

from app.wishlist import api  # noqa: E402, F401
from app.wishlist import controllers  # noqa: E402, F401
from app.wishlist import models  # noqa: E402, F401
from app.wishlist import prisjakt  # noqa: E402, F401