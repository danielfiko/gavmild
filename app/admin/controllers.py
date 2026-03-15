import string
import random
from datetime import datetime, timedelta, timezone

from flask import url_for
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.auth.controllers import hash_password_to_string
from app.auth.models import User, PasswordResetToken
from app.telegram.models import Suggestion, TelegramUser


def get_all_users():
    return db.session.execute(db.select(User).order_by(User.first_name)).scalars().all()


def get_user_details(user_id: int):
    return db.session.get(User, user_id)


def update_user(user_id: int, first_name: str, last_name: str, email: str,
                is_admin: bool, force_pw_change: bool) -> dict:
    user = db.session.get(User, user_id)
    if user is None:
        return {"ok": False, "error": "Bruker ikke funnet"}
    user.first_name = first_name.title()
    user.last_name = last_name.title()
    user.email = email.casefold()
    user.is_admin = is_admin
    user.force_pw_change = 1 if force_pw_change else 0
    try:
        db.session.commit()
        return {"ok": True}
    except SQLAlchemyError:
        db.session.rollback()
        return {"ok": False, "error": "Databasefeil"}


def _generate_code(length: int = 10) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def _unique_token_id(length: int = 5) -> str:
    while True:
        token_id = _generate_code(length)
        if db.session.get(PasswordResetToken, token_id) is None:
            return token_id


def generate_reset_link(user_id: int) -> dict:
    """Create a 15-minute password reset token and return the full URL."""
    user = db.session.get(User, user_id)
    if user is None:
        return {"ok": False, "error": "Bruker ikke funnet"}

    time_now = datetime.now(timezone.utc)
    token_id = _unique_token_id()
    token_string = _generate_code(10)
    hashed_token = hash_password_to_string(token_string)
    reset_token = PasswordResetToken.create(
        token_id=token_id,
        token=hashed_token,
        user_id=user.id,
        expires_at=time_now + timedelta(minutes=15),
    )
    db.session.add(reset_token)
    user.force_pw_change = 1
    try:
        db.session.commit()
        url = url_for(
            "auth.user_reset_password",
            token=f"{token_id}-{token_string}",
            name=user.first_name,
            _external=True,
        )
        return {"ok": True, "url": url, "name": user.first_name}
    except SQLAlchemyError:
        db.session.rollback()
        return {"ok": False, "error": "Databasefeil"}


def get_all_suggestions(filter: str = "open"):
    """Return suggestions. filter: 'open', 'solved', 'all'."""
    query = db.select(Suggestion).order_by(Suggestion.id.desc())
    if filter == "open":
        query = query.where(Suggestion.solved_at.is_(None), Suggestion.deleted_at.is_(None))
    elif filter == "solved":
        query = query.where(Suggestion.solved_at.isnot(None))
    return db.session.execute(query).scalars().all()


def solve_suggestion(suggestion_id: int) -> dict:
    suggestion = db.session.get(Suggestion, suggestion_id)
    if suggestion is None:
        return {"ok": False, "error": "Ikke funnet"}
    suggestion.solved_at = datetime.now(timezone.utc)
    try:
        db.session.commit()
        return {"ok": True}
    except SQLAlchemyError:
        db.session.rollback()
        return {"ok": False, "error": "Databasefeil"}


def delete_suggestion(suggestion_id: int) -> dict:
    suggestion = db.session.get(Suggestion, suggestion_id)
    if suggestion is None:
        return {"ok": False, "error": "Ikke funnet"}
    suggestion.deleted_at = datetime.now(timezone.utc)
    try:
        db.session.commit()
        return {"ok": True}
    except SQLAlchemyError:
        db.session.rollback()
        return {"ok": False, "error": "Databasefeil"}


def get_all_telegram_users():
    return db.session.execute(db.select(TelegramUser).order_by(TelegramUser.id)).scalars().all()


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
