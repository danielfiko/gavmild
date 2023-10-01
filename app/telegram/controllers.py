from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from flask import Blueprint, jsonify, request, abort, current_app
from functools import wraps


telegram_bp = Blueprint("telegram_bot", __name__, url_prefix='/telegram')
API_KEY = 'Your-API-Key'  # Replace with your actual API key


def require_api_key(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if request.headers.get('X-Api-Key') != API_KEY:
            abort(401, 'Invalid API Key')
        return view_function(*args, **kwargs)
    return decorated_function

@telegram_bp.route('/api/data', methods=['GET'])
@require_api_key
def get_data():
    data = {"message": "Hello, Bot!"}
    return jsonify(data)


# @telegram_bp.post("/suggestion")
# def suggestion():
#     msg = ""
#     msg_cont = update.message.text.partition(' ')[2]
#     if not msg_cont:
#         context.bot.send_message(chat_id=update.effective_chat.id, text='Du må skrive "/forslag Dette er mitt forslag"')
#         return "ok"

#     user = TelegramUser.query.get(update.message.from_user.id)
#     if not user:
#         user = TelegramUser(id=update.message.from_user.id, username=update.message.from_user.username)
#         try:
#             db.session.add(user)
#             db.session.commit()
#         except:
#             msg = "Det oppstod en feil (1)."

#     if user:
#         if user.username != update.message.from_user.username:
#             user.username = update.message.from_user.username
#         suggestion = Suggestion(user_id=update.message.from_user.id, suggestion=msg_cont)
#         try:
#             db.session.add(suggestion)
#             db.session.commit()
#             msg = "Takk, forslaget har blitt lagt til"
#         except:
#             msg = "Det oppstod en feil (2)."

#     context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


# def slett(update: Update, context: CallbackContext):
#     if context.args[0] == "siste":
#         suggestion = Suggestion.query.order_by(desc(Suggestion.id)).first()
#     else:
#         suggestion = Suggestion.query.get(int(context.args[0]))
#     if update.message.from_user.id == 79156661:
#         if suggestion:
#             try:
#                 db.session.delete(suggestion)
#                 db.session.commit()
#                 msg = 'Forslaget "' + suggestion.suggestion + '" ble slettet fordi det var idiotisk.'
#             except:
#                 msg = "Noe gikk galt"
#         else:
#             msg = "Fant ikke ønsket med denne IDen"
#         context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
#     else:
#         context.bot.send_message(chat_id=update.effective_chat.id,
#                                  text="Du er ikke verdig til å utføre denne handlingen")


# def solve(update: Update, context: CallbackContext):
#     if update.message.from_user.id == 79156661:
#         suggestion = Suggestion.query.get(int(context.args[0]))
#         if suggestion:
#             try:
#                 db.session.delete(suggestion)
#                 db.session.commit()
#                 msg = 'Forslaget "' + suggestion.suggestion + '" har blitt utført og fjernet fra listen.'
#             except:
#                 msg = "Noe gikk galt"
#         else:
#             msg = "Fant ikke ønsket med denne IDen"
#         context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
#     else:
#         context.bot.send_message(chat_id=update.effective_chat.id,
#                                  text="Du er ikke verdig til å utføre denne handlingen")




###########

# import requests

# url = 'http://your_flask_container:5000/api/data'
# headers = {'X-Api-Key': 'Your-API-Key'}  # Replace with your actual API key

# response = requests.get(url, headers=headers)

# if response.status_code == 200:
#     print(response.json())  # Success!
# else:
#     print("Failed to make request.")  # Invalid API Key or the server encountered an error

# import httpx

# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#   url = 'http://gavmild_backend:5005/api/data'
#   headers = {'X-Api-Key': 'Your-API-Key'}  # Replace with your actual API key

#   async with httpx.AsyncClient() as client:
#       response = await client.get(url, headers=headers)

#   if response.status_code == 200:
#       data = response.json()
#       await context.bot.send_message(chat_id=update.effective_chat.id, text=data['message'])