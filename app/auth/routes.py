from datetime import datetime, timezone

from flask import render_template, redirect, url_for, flash, abort, jsonify, request
from flask_login import login_required, login_user, logout_user, current_user
from sqlalchemy.exc import SQLAlchemyError

from app import bcrypt
from app import db
from app.forms import RegisterForm, LoginForm, ChangePasswordForm
from app.auth import auth_bp
from app.auth.models import User
from app.auth.decorators import token_required
from app.wishlist.controllers import get_users_ordered_by_settings, logged_in_content #TODO: Denne må i et felles område
from app.auth.controllers import generate_unique_code, hash_password_to_string, register_user, log_user_login, handle_valid_token, authenticate_user
from app.admin.decorators import admin_required


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    from app.telegram.controllers import generate_unique_code as tg_generate_unique_code
    from app.telegram.models import TelegramUserConnection

    template_name = "dashboard.html"
    page_title = "Dashboard"
    credentials = None
    if len(current_user.webauthn_credentials) > 0:
        credentials = current_user.webauthn_credentials

    # Telegram connect section
    telegram_bot_url = None
    if not current_user.chat_user:
        connect_id = db.session.scalars(
            db.select(TelegramUserConnection)
            .where(TelegramUserConnection.user_id == current_user.id)
        ).first()
        if not connect_id:
            identifier = tg_generate_unique_code(TelegramUserConnection)
            connect_id = TelegramUserConnection.create(identifier=identifier, user_id=current_user.id)
            db.session.add(connect_id)
            try:
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
                connect_id = None
        if connect_id:
            from flask import current_app
            bot_username = current_app.config.get("TELEGRAM_BOT_USERNAME")
            telegram_bot_url = f"https://t.me/{bot_username}?start={connect_id.identifier}"

    previous_site = request.referrer
    
    if not previous_site or previous_site == request.url:
        previous_site = url_for('index')

    return logged_in_content(
        template_name,
        page_title=page_title,
        credentials=credentials,
        telegram_connected=bool(current_user.chat_user),
        telegram_bot_url=telegram_bot_url,
        previous_site=previous_site,
    )


@auth_bp.route("/dashboard/add-security-key", methods=["GET"])
@login_required
def handler_add_security_key():
    if request.method == "GET":
        template_name = "add_security_key.html"
        page_title = "Passordløs innlogging"
        breadcrumb_path = url_for("auth.dashboard")
        credentials = current_user.webauthn_credentials

        return render_template(template_name,
                               page_title=page_title,
                               breadcrumb_path=breadcrumb_path,
                               credentials=credentials)
    if request.method == "POST":
        return "OK", 200
    abort(405)


@auth_bp.route("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("wishlist.index"))
    else:
        return render_template("login.html", form=LoginForm())


@auth_bp.route("/superhemmelig-lag-konto-side")
def register():  # TODO: SECURITY - Registration is "hidden" by obscure URL. Use proper invite codes or admin approval instead of security through obscurity.
    return render_template("register.html", form=RegisterForm())


@auth_bp.route("/api/login", methods=["POST"])
def login_api():
    form = LoginForm()
    if not form.validate_on_submit():
        flash("Skjema ble ikke validert.")
        return redirect(url_for("auth.login"))
    user = authenticate_user(form.email.data, form.password.data)
    if not user:
        flash("Feil brukernavn eller passord")
        return redirect(url_for("auth.login"))

    if user.force_pw_change:
        return render_template("change_pw.html", form=form, email=form.email.data,
                                temp_password_required=True)
    login_user(user, remember=form.remember_me.data)
    log_user_login(user.id, "password")
    return redirect(url_for("wishlist.index"))


@auth_bp.route("/api/change-pw", methods=["POST"])
def change_pw():
    form = LoginForm()
    if not form.validate_on_submit():
        return "Skjema ble ikke validert"

    assert form.new_password.data is not None
    user = db.session.execute(
        db.select(User).where(User.email == form.email.data)
    ).scalar_one_or_none()
    if not user:
        return "Finner ikke bruker"
    if not bcrypt.check_password_hash(user.password, form.password.data):
        return "Gammelt passord er feil"
    if len(form.new_password.data) < 8:
        return "Passordet er for kort"
    
    hashed_password = hash_password_to_string(form.new_password.data)
    user.password = hashed_password
    user.force_pw_change = 0
    db.session.commit()
    
    login_user(user)  # Login AFTER successful DB commit
    return "Passordet ble endret, videresender til forsiden..."


@auth_bp.route("/api/logout", methods=["POST"])
@login_required
def logout_api():
    logout_user()
    if "token" in request.args:
        name = request.args["name"] if "name" in request.args else None
        return redirect(url_for("auth.user_reset_password", token=request.args["token"], name=name))
    return redirect(url_for("wishlist.index"))



@auth_bp.route("/api/register", methods=["POST"])
def register_api():
    form = RegisterForm()
    if not form.validate_on_submit():
        return "Noe gikk galt, registreringen ble ikke fullført"
    try:
        register_user(form)
        db.session.commit()
    except ValueError as e:
        db.session.rollback()
        return str(e)
    
    return redirect(url_for("auth.login"))


@auth_bp.post("/api/settings/order_by")
@login_required
def set_order_by():
    order_by_value = request.form.get("order_by")
    if order_by_value not in {"birthday", "first_name"}:
        abort(400, "Ugyldig order_by verdi")
    user = db.session.get(User, current_user.id)
    if user is None:
        abort(404, "Bruker ikke funnet")
    user.preferences.order_users_by = order_by_value
    users: list[dict[str, str]] = [{"first_name": u.first_name, "path": url_for('wishlist.user', user_id=u.id)} for u in
             get_users_ordered_by_settings()]
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        abort(500, "Database error")
    
    return jsonify(users)


@auth_bp.get("/auth/reset-password")
@login_required
@admin_required
def forgot_password():
    users = db.session.execute(db.select(User.first_name, User.id)).mappings()

    return render_template("reset-password.html", users=users)


@auth_bp.post("/api/reset-password/")
@login_required
@admin_required
def reset_password():
    user = db.session.get(User, request.form.get("user_id"))
    if user is None:
        abort(404)
    temp_password = generate_unique_code()
    hashed_password = hash_password_to_string(temp_password)
    user.password = hashed_password
    user.force_pw_change = 1
    db.session.commit()

    return {"first_name": user.first_name, "password": temp_password}


@auth_bp.get("/bytt-passord/<token>")
@token_required
def user_reset_password(token_entry):
    name = request.args.get("name", "")
    return handle_valid_token(token_entry, name)


@auth_bp.post("/bytt-passord/<token>")
@token_required
def user_change_password(token_entry):
    form = ChangePasswordForm()
    name = request.args.get("name")

    if form.validate_on_submit():
        assert form.new_password.data is not None
        user = token_entry.user
        new_password = form.new_password.data
        hashed_password = hash_password_to_string(new_password)
        user.password = hashed_password
        user.force_pw_change = 0
        token_entry.used_at = datetime.now(timezone.utc)
        db.session.commit()
        flash("Passordet ble endret, vennligst logg inn på nytt.")
        return redirect(url_for("auth.login"))

    else:
        return render_template("change_pw.html", form=form, name=name)
