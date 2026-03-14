import os

from flask import Blueprint

APP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(APP_PATH, 'templates/telegram')

telegram_bp = Blueprint("telegram_bot", __name__, url_prefix='/telegram', template_folder=TEMPLATE_PATH)

from app.telegram import bot
from app.telegram import controllers
from app.telegram import models