from queue import Queue
from threading import Thread
import telegram
from flask import Blueprint, request
from telegram import Update
from telegram.ext import Dispatcher, CommandHandler, CallbackContext
from ... import app
from . import bot

bot_app = Blueprint("bot", __name__, url_prefix='/bot')


def forslag(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Hei " + update.message.from_user.username)
    # update.message.text.partition(' ')[2]


# Create bot, update queue and dispatcher instances
update_queue = Queue()
dispatcher = Dispatcher(bot, update_queue)
dispatcher.add_handler(CommandHandler("hei", forslag))

# Start the thread
thread = Thread(target=dispatcher.start, name='dispatcher')
thread.start()

# return q
# you might want to return dispatcher as well,
# to stop it at server shutdown, or to register more handlers:
# return (update_queue, dispatcher)


@bot_app.route('/{}'.format(app.config["TELEGRAM_TOKEN"]), methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    update_queue.put(update)
    return "ok"
