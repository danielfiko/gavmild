from telegram import Bot
from app import app


bot = Bot(app.config["TELEGRAM_TOKEN"])