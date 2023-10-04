from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from flask import Blueprint, jsonify, request, abort, current_app, render_template, flash
from flask_login import login_required, current_user
from functools import wraps
from app.database.database import db
from app.telegram.models import TelegramUser, Suggestion, TelegramUserConnection
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import random
import string
from app.forms import TelegramConnectForm
import os


APP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(APP_PATH, 'templates/telegram')

telegram_bp = Blueprint("telegram_bot", __name__, url_prefix='/telegram', template_folder=TEMPLATE_PATH)

filter_active_suggestions = (Suggestion.solved_at == None) & (Suggestion.deleted_at == None)


def require_api_key(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if request.headers.get('X-Api-Key') != current_app.config["BOT_API_TOKEN"]:
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
def add_suggestion():
    json_data = request.get_json()
    req_username = json_data.get('username')
    req_id = json_data.get('id')
    req_suggestion = json_data.get("suggestion")

    user = TelegramUser.query.get(req_id)

    if not user:
        user = TelegramUser(id=req_id, chat_username=req_username)
        try:
            db.session.add(user)
            db.session.commit()
        except:
            pass

    if user.chat_username != req_username:
        user.chat_username = req_username
    suggestion = Suggestion(user_id=req_id, suggestion=req_suggestion)
    try:
        db.session.add(suggestion)
        db.session.commit()
        return jsonify(success=True)
    except:
        pass
    
    return jsonify(success=False)


def get_suggestion(json_data):
    req_suggestion_id = json_data.get('suggestion_id')
 
    if req_suggestion_id == "siste":
        suggestion = db.session.execute(db.select(Suggestion)
                                        .where(filter_active_suggestions)
                                        .order_by(desc(Suggestion.id))
                                        ).scalars().first()
    else:
        suggestion = db.get_or_404(Suggestion, int(req_suggestion_id))

    return suggestion


@telegram_bp.delete("/suggestion")
@require_api_key
def delete_suggestion():
    suggestion = get_suggestion(request.get_json())
    suggestion.deleted_at = datetime.utcnow()
    try:
        db.session.commit()
        return jsonify({"message": suggestion.suggestion})
    except:
        abort(500, 'Noe gikk galt, kunne ikke slette ønsket.')


@telegram_bp.post("/solve")
@require_api_key
def solve_suggestion():
    suggestion = get_suggestion(request.get_json())
    suggestion.solved_at = datetime.utcnow()
    try:
        db.session.commit()
        return jsonify({"message": suggestion.suggestion})
    except:
        abort(500, 'Noe gikk galt, kunne ikke slette ønsket.')



@telegram_bp.get("/connect")
@login_required
def connect_code():
    connect_id = db.session.scalars(
        db.select(TelegramUserConnection)
        .where(TelegramUserConnection.user_id == current_user.id)
        ).first()
    
    def generate_unique_code(length=10):
        characters = string.ascii_letters + string.digits
        unique_code = ''.join(random.choice(characters) for _ in range(length))
        return unique_code

    def is_unique_primary_key(primary_key):
        # Check if the primary key already exists in the database
        existing_record = db.session.get(TelegramUserConnection, primary_key)
        return existing_record is None

    def generate_connection_code():
        while True:
            unique_code = generate_unique_code()
            if is_unique_primary_key(unique_code):
                return unique_code
    

    if not connect_id:
        identifier = generate_connection_code()
        connect_id = TelegramUserConnection(identifier=identifier, user_id=current_user.id)
        db.session.add(connect_id)
    
    form = TelegramConnectForm()

    try:
        db.session.commit()
        bot_url=f"https://t.me/onske_bot?start={connect_id.identifier}"
        return render_template("connect-user.html", form=form, bot_url=bot_url)
    
    except SQLAlchemyError as e:
        flash(str(e.orig))
        return render_template("connect-user.html")


@telegram_bp.post("/connect-user")
@require_api_key
def connect_user():
    json_data = request.get_json()
    chat_user_id = json_data.get('chat_user_id')
    chat_username = json_data.get('chat_username')
    identifier = json_data.get('identifier')

    connect_id = db.get_or_404(TelegramUserConnection, identifier)
    telegram_user = db.session.get(TelegramUser, chat_user_id)

    if telegram_user:
        telegram_user.user_id = connect_id.user_id
    else:
        telegram_user = TelegramUser(id=chat_user_id, chat_username=chat_username, user_id=connect_id.user_id)
        db.session.add(telegram_user)
    try:
        db.session.delete(connect_id)
        db.session.commit()
        return jsonify(username=telegram_user.user.username)
    except SQLAlchemyError as e:
        abort(500, str(e.orig))