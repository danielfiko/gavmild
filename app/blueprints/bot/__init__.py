from queue import Queue
from threading import Thread
from telegram import Bot, Update
from telegram.ext import Dispatcher, CallbackContext, CommandHandler
from app import app


def forslag(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Takk for forslaget, jeg har lagt det til i listen.")


# Create bot, update queue and dispatcher instances
bot = Bot(app.config["TELEGRAM_TOKEN"])
update_queue = Queue()

dispatcher = Dispatcher(bot, update_queue)

dispatcher.add_handler(CommandHandler("forslag", forslag))

# Start the thread
thread = Thread(target=dispatcher.start, name='dispatcher')
thread.start()

#return q
# you might want to return dispatcher as well,
# to stop it at server shutdown, or to register more handlers:
# return (update_queue, dispatcher)
