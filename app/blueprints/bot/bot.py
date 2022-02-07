import telegram
from flask import Blueprint, request
from . import update_queue
from ... import app
from . import bot

bot_app = Blueprint("bot", __name__, url_prefix='/bot')


@bot_app.route('/{}'.format(app.config["TELEGRAM_TOKEN"]), methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    update_queue.put(update)
    return
