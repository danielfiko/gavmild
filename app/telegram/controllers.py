from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from flask import Blueprint, jsonify, request, abort, current_app
from functools import wraps
from app.database.database import db
from app.telegram.models import TelegramUser, Suggestion


telegram_bp = Blueprint("telegram_bot", __name__, url_prefix='/telegram')


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


@telegram_bp.post("/suggestion")
@require_api_key
def suggestion():
    json_data = request.get_json()
    req_username = json_data.get('username')
    req_id = json_data.get('id')
    req_suggestion = json_data.get("suggestion")

    user = TelegramUser.query.get(req_id)

    if user:
        if user.username != req_username:
            user.username = req_username
        suggestion = Suggestion(user_id=req_id, suggestion=req_suggestion)
        try:
            db.session.add(suggestion)
            db.session.commit()
            return jsonify(success=True)
        except:
            pass
    else:
        user = TelegramUser(id=req_id, username=req_username)
        try:
            db.session.add(user)
            db.session.commit()
            return jsonify(success=True)
        except:
            pass
    
    return jsonify(success=False)


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