from queue import Queue
from threading import Thread
import telegram
from flask import Blueprint, request
from sqlalchemy import desc
from telegram import Update
from telegram.ext import Dispatcher, CommandHandler, CallbackContext
from ... import app, db
from . import bot
from ...models import TelegramUser, Suggestion
from bs4 import BeautifulSoup as bs
import requests
import validators

bot_app = Blueprint("bot", __name__, url_prefix='/bot')


def start(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Hei! Jeg kan legge til nye forslag du har for "
                            "ønskelisteappen, bare skriv /forslag <ditt "
                            "forslag> i chatten.")


def forslag(update: Update, context: CallbackContext):
    msg = ""
    msg_cont = update.message.text.partition(' ')[2]
    if not msg_cont:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Du må skrive "/forslag Dette er mitt forslag"')
        return "ok"

    user = TelegramUser.query.get(update.message.from_user.id)
    if not user:
        user = TelegramUser(id=update.message.from_user.id, username=update.message.from_user.username)
        try:
            db.session.add(user)
            db.session.commit()
        except:
            msg = "Det oppstod en feil (1)."

    if user:
        if user.username != update.message.from_user.username:
            user.username = update.message.from_user.username
        suggestion = Suggestion(user_id=update.message.from_user.id, suggestion=msg_cont)
        try:
            db.session.add(suggestion)
            db.session.commit()
            msg = "Takk, forslaget har blitt lagt til"
        except:
            msg = "Det oppstod en feil (2)."

    context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


def slett(update: Update, context: CallbackContext):
    if context.args[0] == "siste":
        suggestion = Suggestion.query.order_by(desc(Suggestion.id)).first()
    else:
        suggestion = Suggestion.query.get(int(context.args[0]))
    if update.message.from_user.id == 79156661:
        if suggestion:
            try:
                db.session.delete(suggestion)
                db.session.commit()
                msg = 'Forslaget "' + suggestion.suggestion + '" ble slettet fordi det var idiotisk.'
            except:
                msg = "Noe gikk galt"
        else:
            msg = "Fant ikke ønsket med denne IDen"
        context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Du er ikke verdig til å utføre denne handlingen")


def løst(update: Update, context: CallbackContext):
    if update.message.from_user.id == 79156661:
        suggestion = Suggestion.query.get(int(context.args[0]))
        if suggestion:
            try:
                db.session.delete(suggestion)
                db.session.commit()
                msg = 'Forslaget "' + suggestion.suggestion + '" har blitt utført og fjernet fra listen.'
            except:
                msg = "Noe gikk galt"
        else:
            msg = "Fant ikke ønsket med denne IDen"
        context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Du er ikke verdig til å utføre denne handlingen")


def solve(update: Update, context: CallbackContext):
    url = update.message.text.partition(' ')[2]
    if validators.url(url):
        response = requests.get(url)
        html = response.content
        soup = bs(html)
        body = soup.body


# Create bot, update queue and dispatcher instances
update_queue = Queue()
dispatcher = Dispatcher(bot, update_queue)
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("forslag", forslag))
dispatcher.add_handler(CommandHandler("slett", slett))
dispatcher.add_handler(CommandHandler("solve", solve))

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
