import logging
import os
import random
import string
from datetime import datetime, timedelta, timezone

import requests
from flask import current_app, redirect, flash, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError

from app import api_login_required, db
from app.auth.controllers import hash_password_to_string
from app.auth.models import PasswordResetToken, User
from app.forms import APIform
from app.telegram import telegram_bp
from app.telegram.models import (
    ReportedLink,
    Suggestion,
    TelegramUser,
    TelegramUserConnection,
)
from app.wishlist.models import Wish

filter_active_suggestions = (Suggestion.solved_at is None) & (Suggestion.deleted_at is None)

class APIerror(Exception):
    pass


# ---------------------------------------------------------------------------
# Service functions (called directly by bot handlers in bot.py)
# ---------------------------------------------------------------------------

def svc_add_suggestion(username, user_id, suggestion_text):
    """Create a suggestion from a Telegram user. Returns True on success."""
    user = db.session.get(TelegramUser, user_id)
    if not user:
        user = TelegramUser.create(id=user_id, chat_username=username)
    elif user.chat_username != username:
        user.chat_username = username
    Suggestion.create(user_id=user_id, suggestion=suggestion_text)
    try:
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.getLogger(__name__).error(f"Failed to add suggestion: {e}")
        return False
    return True


def _get_suggestion_by_id(suggestion_id):
    """Fetch an active suggestion by numeric id or 'siste' (latest)."""
    if suggestion_id == "siste":
        return db.session.execute(
            db.select(Suggestion)
            .where(filter_active_suggestions)
            .order_by(desc(Suggestion.id))
        ).scalars().first()
    try:
        return db.session.get(Suggestion, int(suggestion_id))
    except (ValueError, TypeError):
        return None


def svc_delete_suggestion(suggestion_id):
    """Soft-delete a suggestion. Returns dict with ok/message/not_found keys."""
    suggestion = _get_suggestion_by_id(suggestion_id)
    if not suggestion:
        return {"ok": False, "not_found": True}
    suggestion.deleted_at = datetime.now(timezone.utc)
    try:
        db.session.commit()
        return {"ok": True, "message": suggestion.suggestion}
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.getLogger(__name__).error(f"Failed to delete suggestion: {e}")
        return {"ok": False}


def svc_solve_suggestion(suggestion_id):
    """Mark a suggestion as solved. Returns dict with ok/message/not_found keys."""
    suggestion = _get_suggestion_by_id(suggestion_id)
    if not suggestion:
        return {"ok": False, "not_found": True}
    suggestion.solved_at = datetime.now(timezone.utc)
    try:
        db.session.commit()
        return {"ok": True, "message": suggestion.suggestion}
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.getLogger(__name__).error(f"Failed to solve suggestion: {e}")
        return {"ok": False}


def svc_connect_user(chat_user_id, chat_username, identifier):
    """Link a Telegram user to a webapp account via connection code.
    Returns dict with ok/username, or ok=False with not_found key."""
    connect_id = db.session.get(TelegramUserConnection, identifier)
    if not connect_id:
        logging.getLogger(__name__).warning(f"Failed to connect user: {identifier} not found")
        return {"ok": False, "not_found": True}
    telegram_user = db.session.get(TelegramUser, chat_user_id)
    if telegram_user:
        telegram_user.user_id = connect_id.user_id
    else:
        telegram_user = TelegramUser.create(
            id=chat_user_id, chat_username=chat_username, user_id=connect_id.user_id
        )
    try:
        db.session.delete(connect_id)
        db.session.commit()
        return {"ok": True, "username": telegram_user.user.username}
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.getLogger(__name__).error(f"Failed to connect user: {e}")
        return {"ok": False}


def svc_get_users():
    """Return list of dicts with id and first_name for all users."""
    try:
        rows = db.session.execute(db.select(User.id, User.first_name)).mappings().all()
        return [{"id": r["id"], "first_name": r["first_name"]} for r in rows]
    except SQLAlchemyError as e:
        logging.getLogger(__name__).error(f"Failed to get users: {e}")
        return None


def svc_get_reset_token(chat_user_id):
    """Generate a password-reset token for the user linked to chat_user_id.
    Returns dict with ok/token/name, or ok=False with not_found/rate_limited keys."""
    chat_user = db.session.get(TelegramUser, chat_user_id)
    if not chat_user:
        return {"ok": False, "not_found": True}

    time_now = datetime.now(timezone.utc)
    user = chat_user.user

    if db.session.execute(
        db.select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.expires_at > time_now,
            PasswordResetToken.used_at.is_(None),
        )
    ).first():
        return {"ok": False, "rate_limited": True}

    expires_at = time_now + timedelta(minutes=15)
    token_id = generate_unique_code(PasswordResetToken, 5)
    token_string = generate_code(10)
    hashed_token = hash_password_to_string(token_string)
    reset_token = PasswordResetToken.create(
        token_id=token_id, token=hashed_token, user_id=user.id, expires_at=expires_at
    )
    db.session.add(reset_token)
    try:
        db.session.commit()
        return {"ok": True, "token": f"{token_id}-{token_string}", "name": user.first_name}
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.getLogger(__name__).error(f"Failed to create reset token: {e}")
        return {"ok": False}


# ---------------------------------------------------------------------------
# Helpers (used by service functions and web routes below)
# ---------------------------------------------------------------------------

def generate_code(length=10):
    characters = string.ascii_letters + string.digits
    unique_code = ''.join(random.choice(characters) for _ in range(length))
    return unique_code

def is_unique_primary_key(model, primary_key):
    # Check if the primary key already exists in the database
    existing_record = db.session.get(model, primary_key)
    return existing_record is None

def generate_unique_code(model, length=None):
    length = length or 10
    while True:
        unique_code = generate_code(length)
        if is_unique_primary_key(model, unique_code):
            return unique_code

def unlink_telegram_user(telegram_id: int) -> dict:
    tg_user = db.session.get(TelegramUser, telegram_id)
    if tg_user is None:
        return {"ok": False, "error": "Ikke funnet"}
    tg_user.user_id = None
    try:
        db.session.commit()
        return {"ok": True}
    except SQLAlchemyError:
        db.session.rollback()
        return {"ok": False, "error": "Databasefeil"}

@telegram_bp.get("/connect")
@login_required
def connect_code():
    return redirect(url_for("auth.dashboard"))

@telegram_bp.post("/disconnect")
@login_required
def disconnect():
    result = unlink_telegram_user(current_user.chat_user.id)
    if result["ok"]:
        flash("Telegram-bruker koblet fra.", "success")
    else:
        flash(result.get("error", "Noe gikk galt."), "error")
    return redirect(url_for("auth.dashboard"))

def telegram_escape_text(input_string):
    escaped_string = input_string.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")
    return escaped_string

def telegram_bot_sendtext(chat_id, message):
    try:
        bot_token = current_app.config["TELEGRAM_TOKEN"]
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
            "text": message
        }
        response = requests.post(url, data=payload)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx status codes)

    except requests.HTTPError as e:
        # Handle HTTP errors (4xx and 5xx status codes)
        current_app.logger.error(f"HTTP Error: {e.response.status_code}")
        raise APIerror() # Re-raise the exception after handling it, or handle it as appropriate for your application

    except requests.RequestException as e:
        # Handle request exceptions (e.g., network issues, timeouts)
        current_app.logger.error(f"Request Exception: {e}")
        raise APIerror()  # Re-raise the exception after handling it, or handle it as appropriate for your application

    except Exception as e:
        # Handle other exceptions
        current_app.logger.error(f"An error occurred: {e}")
        raise APIerror() # Re-raise the exception after handling it, or handle it as appropriate for your application

    else:
        # Code to run if there are no exceptions
        current_app.logger.info("Message sent successfully")

    finally:
        # Cleanup code (if any)
        pass

@telegram_bp.post("/report-link")
@api_login_required
def report_link():
    form = APIform()
    if form.validate_on_submit():
        reported_wish_id = int(request.values.get("id"))
        report_confirmed = True if request.values.get("confirmed") == "true" else False
        link_report = db.session.get(ReportedLink, reported_wish_id)
        
        modal_title = "Rapporter død lenke?"
        modal_message = ""
        modal_buttons = ""

        if link_report:
            modal_message = "Det er allerede sendt en beskjed om denne lenken."
            modal_buttons = "close"
            return render_template(
                "/wishlist/modal/action_confirmation.html",
                title=modal_title, message=modal_message, buttons=modal_buttons, form=form)

        elif report_confirmed:
            link_report = ReportedLink(wish_id=reported_wish_id, reported_by_user_id=current_user.id)
            wish = db.session.get(Wish, reported_wish_id)

            try:
                db.session.add(link_report)
                user_first_name = telegram_escape_text(wish.user.first_name)
                wish_title = telegram_escape_text(wish.title)
                wish_url = telegram_escape_text(f"gavmild.dfiko.no/user/{wish.user.id}/wish/{wish.id}")
                message = (
                    f"Hei {user_first_name}!\n\n"
                    f"Noen har meldt at lenken du har lagt til for ønsket *{wish_title}* ikke fungerer.\n\n"
                    f"Vennligst sjekk lenken og oppdater den hvis det er nødvendig.\n\n{wish_url}"
                )

                chat_user = wish.user.chat_user
                chat_user_id = ""
                
                if not chat_user:
                    chat_user_id = os.getenv("TELEGRAM_GROUP_ID") #TODO: Sentralisere uthenting av dette?
                    message += "\n\nDenne meldingen ble sendt her siden du ikke har koblet Telegram-kontoen din til Gavmild. Vennligst gå inn på https://gavmild.dfiko.no/telegram/connect for å gjøre det så snart som mulig."
                
                else:
                    chat_user_id = wish.user.chat_user.id
                
                telegram_bot_sendtext(chat_user_id, message)
                db.session.commit()
                modal_message = "Meldingen ble sendt, takk for at du ga beskjed."
                modal_buttons = "close"
 
            except SQLAlchemyError:
                db.session.rollback()
                modal_title = "Noe gikk galt"
                modal_message = "Det oppstod en feil under lagring av feilmeldingen. Prøv igjen."
                modal_buttons = "close"
            
            except APIerror:
                modal_title = "Noe gikk galt"
                modal_message = "Det oppstod en feil og beskjeden kunne ikke sendes. Prøv igjen."
                modal_buttons = "close"

            finally:
                return render_template(
                    "/wishlist/modal/action_confirmation.html",
                    title = modal_title,
                    message = modal_message,
                    buttons = modal_buttons,
                    form=form)

        else:
            wish = db.session.get(Wish, reported_wish_id)
            
            if wish:
                return render_template(
                    "/wishlist/modal/action_confirmation.html",
                    title = modal_title,
                    message = f"Det blir sendt en melding til {wish.user.first_name} om at lenken ikke fungerer.",
                    buttons = "confirm",
                    form=form)

    return render_template(
        "/wishlist/modal/action_confirmation.html",
        title = "Det oppstod en feil",
        message = '''Handlingen kunne ikke fullføres på grunn av en sikkerhetsfeil (CSRF). 
                    Vennligst last inn siden på nytt og prøv igjen. 
                    Hvis problemet vedvarer, kontakt support for assistanse.'''.split('\n'),
        buttons = "close",
        form=form)


