from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from flask import Blueprint, jsonify, request, abort, current_app, render_template, flash, Response
from flask_login import login_required, current_user
from functools import wraps
from app.database.database import db
from app.telegram.models import TelegramUser, Suggestion, TelegramUserConnection, ReportedLink
from app.wishlist.models import Wish
from app.forms import TelegramConnectForm, APIform
from app import read_secret, api_login_required
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import random
import string
import os
import requests


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
        return render_template("connect-user.html", e=e)


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


def telegram_bot_sendtext(chat_id, message):
    print(f"Chat user id: {chat_id}")
    bot_token = read_secret("telegram-token")
    bot_chat_id = str(chat_id)
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chat_id + '&parse_mode=Markdown&disable_web_page_preview=true&text=' + message
    
    response = requests.get(send_text)
    if response.status_code == 200:
        return response
    else:
        raise Exception("Kunne ikke sende melding")


@telegram_bp.post("/report-link")
@api_login_required
def report_link():
    form = APIform()
    if form.validate_on_submit():
        reported_wish_id = int(request.values.get("id"))
        report_confirmed = True if request.values.get("confirmed") == "true" else False
        link_report = db.session.get(ReportedLink, reported_wish_id)
        
        modal_title = "Rapporter død lenke?"

        if link_report:
            modal_message = "Det er allerede sendt en beskjed om denne lenken."
            modal_buttons = "close"
            return render_template(
                "/wishlist/action_confirmation.html",
                title=modal_title, message=modal_message, buttons=modal_buttons, form=form)

        elif report_confirmed:
            link_report = ReportedLink(wish_id=reported_wish_id, reported_by_user_id=current_user.id)
            wish = db.session.get(Wish, reported_wish_id)
            print(wish)
            try:
                db.session.add(link_report)
                message = (
                    f"Hei {wish.user.first_name}!\n\n"
                    f"Noen har meldt at lenken du har lagt til for ønsket *{wish.title}* ikke fungerer.\n\n"
                    f"Vennligst sjekk lenken og oppdater den hvis det er nødvendig.\n\nLenken som er rapportert: {wish.url}"
                )

                print(message)

                chat_user = wish.user.chat_user
                chat_user_id = ""
                if not chat_user:
                    print("joe mama 4")
                    chat_user_id = read_secret("chat-group-id")
                    message += "\n\nDenne meldingen ble sendt her siden du ikke har koblet Telegram-kontoen din til Gavmild. Vennligst gå inn på https://gavmild.dfiko.no/telegram/connect for å gjøre det så snart som mulig."
                else:
                    chat_user_id = wish.user.chat_user.id
                telegram_bot_sendtext(chat_user_id, message)
                db.session.commit()

                modal_message = "Meldingen ble sendt, takk for at du ga beskjed."
                modal_buttons = "close"
            
            except SQLAlchemyError as e:
                #db.session.rollback()  # Rollback changes in case of error
                modal_message = "Noe gikk galt - fikk ikke sendt beskjed (database error)."
                modal_buttons = "close"

            except:
                modal_message = "Noe gikk galt - fikk ikke sendt beskjed (message error)."
                modal_buttons = "close"
            
            finally:
                return render_template(
                    "/wishlist/action_confirmation.html",
                    title = modal_title,
                    message = modal_message,
                    buttons = modal_buttons,
                    form=form)

        else:
            wish = db.session.get(Wish, reported_wish_id)
            
            if wish:
                return render_template(
                    "/wishlist/action_confirmation.html",
                    title = modal_title,
                    message = f"Det blir sendt en melding til {wish.user.first_name} om at lenken ikke fungerer.",
                    buttons = "confirm",
                    form=form)
    
    return render_template(
        "/wishlist/action_confirmation.html",
        title = "Det oppstod en feil",
        message = '''Handlingen kunne ikke fullføres på grunn av en sikkerhetsfeil (CSRF). 
                    Vennligst last inn siden på nytt og prøv igjen. 
                    Hvis problemet vedvarer, kontakt support for assistanse.'''.split('\n'),
        buttons = "close",
        form=form)
