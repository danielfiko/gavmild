from functools import wraps
from datetime import datetime, timezone

from flask import render_template

from app import bcrypt
from app import db
from app.auth.models import PasswordResetToken


def is_valid_token(token_entry: PasswordResetToken, token_string: str) -> bool:
    return (
            token_entry is not None
            and token_entry.expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)
            and not token_entry.used_at
            and bcrypt.check_password_hash(token_entry.token, token_string)
    )

def get_password_reset_token_entry(token_id: str) -> PasswordResetToken | None:
    return db.session.get(PasswordResetToken, token_id)

def extract_token_data(token: str) -> tuple[str | None, str | None]:
    try:
        token_id, token_string = token.split("-")
        return token_id, token_string
    except ValueError:
        return None, None

def get_error_message(message):
    return render_template("change_pw_error.html", message=message)

def token_required(view_function):
    @wraps(view_function)
    def decorated_function(token: str, *args, **kwargs):
        error_message = get_error_message(
            "Beklager, men det ser ut til at lenken du prøver å bruke enten er feil eller ikke er gyldig lenger.")
        
        try:
            token_id, token_string = token.split("-")
        except ValueError:
            return error_message
        
        token_entry = db.session.get(PasswordResetToken, token_id)

        if token_entry and is_valid_token(token_entry, token_string):
            return view_function(token_entry, *args, **kwargs)

        return error_message

    return decorated_function