from datetime import datetime, time
import secrets
import random

from flask_login import current_user
from flask import render_template, url_for, request
from sqlalchemy import exists

from app import bcrypt, db
from app.forms import RegisterForm, ChangePasswordForm
from app.auth.models import User, PasswordResetToken, UserLogin
from app.wishlist.controllers import get_users_ordered_by_settings


def handle_valid_token(token_entry: PasswordResetToken, name: str):
    if current_user.is_authenticated and current_user.id != token_entry.user.id:
        logout_url = url_for(
            "auth.logout_api",
            token=f"{token_entry.token_id}-{token_entry.token}",
            name=name,
        )
        return render_template(
            "change_pw_error.html",
            message=f"Beklager, men det ser ut til at du prøver å endre passordet til en annen bruker enn den som er logget inn. Vennligst <a href='{logout_url}' class='link-accent'>logg ut</a> av den gjeldende brukerkontoen før du forsøker å endre passordet.",
        )

    form = ChangePasswordForm()
    return render_template("change_pw.html", form=form, name=name)


def generate_unique_code(length: int = 10) -> str:
    return secrets.token_urlsafe(length)[:length]


def email_exists(email: str) -> bool:
    return db.session.query(exists().where(User.email == email)).scalar()


def generate_unique_username(first_name: str, last_name: str) -> str | None:
    base_username = first_name.split()[0].casefold() + last_name[:1].casefold()

    username = base_username

    for _ in range(10):
        existing = db.session.execute(
            db.select(User).where(User.username == username)
        ).scalar_one_or_none()
        if not existing:
            return username
        username = f"{base_username}{random.randint(10, 99)}"

    return None


def hash_password_to_string(password: str) -> str:
    return bcrypt.generate_password_hash(password).decode("utf-8")


def register_user(form: RegisterForm) -> User:
    assert form.email.data is not None
    assert form.first_name.data is not None
    assert form.last_name.data is not None
    assert form.password.data is not None
    assert form.date_of_birth.data is not None

    if email_exists(form.email.data):
        raise ValueError("E-post allerede registrert.")

    username = generate_unique_username(form.first_name.data, form.last_name.data)
    if not username:
        raise ValueError("Det oppstod en feil ved registrering av brukeren")
    hashed_password = hash_password_to_string(form.password.data)
    user = User.create(
        first_name=form.first_name.data,
        last_name=form.last_name.data,
        email=form.email.data,
        hashed_password=hashed_password,
        date_of_birth=datetime.combine(form.date_of_birth.data, time.min),
        username=username,
    )

    db.session.add(user)
    return user


def get_user_by_email(email: str) -> User | None:
    user = db.session.execute(
        db.select(User).where(User.email == email)
    ).scalar_one_or_none()
    return user


def log_user_login(user_id: int, login_type: str, entry_id: int | None = None):
    ip_address = (
        request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"
    )
    user_agent = request.user_agent.string
    login_entry = UserLogin.create(
        user_id=user_id,
        login_type=login_type,
        ip_address=ip_address,
        user_agent=user_agent,
        credential=entry_id,
    )
    db.session.add(login_entry)
    db.session.commit()


def authenticate_user(email, password):
    user = db.session.execute(
        db.select(User).where(User.email == email)
    ).scalar_one_or_none()
    if not user or not bcrypt.check_password_hash(user.password, password):
        return None
    return user


def get_users_ordered_by(order_by: str) -> list[dict]:
    return [
        {"first_name": u.first_name, "path": url_for("wishlist.user", user_id=u.id)}
        for u in get_users_ordered_by_settings()
    ]
