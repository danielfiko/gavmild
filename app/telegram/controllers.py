from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from flask import Blueprint, jsonify, request, abort, current_app
from functools import wraps
from app.database.database import db
from app.telegram.models import TelegramUser, Suggestion
from sqlalchemy import desc
from datetime import datetime


telegram_bp = Blueprint("telegram_bot", __name__, url_prefix='/telegram')

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

    if user:
        if user.chat_username != req_username:
            user.chat_username = req_username
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
