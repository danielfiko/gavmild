import os

from flask import Blueprint

APP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(APP_PATH, 'templates/wishlist')

extractor_bp = Blueprint('product_extractor', __name__,
                        url_prefix='/', template_folder=TEMPLATE_PATH)  # static_folder='static/views'

from app.wishlist.product_extractor import product_extractor  # noqa: E402, F401