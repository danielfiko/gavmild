from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, abort, jsonify, request
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from app.forms import RegisterForm, LoginForm, ChangePasswordForm
#from app.blueprints.auth.models import User
import random as rand
from app.database.database import db
from app.auth.models import User, PasswordResetToken
from app.telegram.models import TelegramUser
import os
from sqlalchemy.exc import SQLAlchemyError
import random
import string


APP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(APP_PATH, 'templates/auth')

login_manager = LoginManager()
login_manager.login_view = "auth.login"
bcrypt = Bcrypt()


class PasswordTokenError(Exception):
    pass


def generate_unique_code(length=10):
    characters = string.ascii_letters + string.digits
    unique_code = ''.join(random.choice(characters) for _ in range(length))
    return unique_code


def init_auth(app):
    bcrypt.init_app(app)
    login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

auth_bp = Blueprint('auth', __name__, template_folder=TEMPLATE_PATH)

###########


@auth_bp.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    return render_template("dashboard.html")


@auth_bp.route("/login")
def login():
    form = LoginForm()
    return render_template("login.html", form=form)


@auth_bp.route("/superhemmelig-lag-konto-side")
def register():
    form = RegisterForm()
    return render_template("register.html", form=form)


@auth_bp.route("/api/login", methods=["POST"])
def login_api():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).where(User.email == form.email.data)).scalar_one_or_none()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                if user.force_pw_change:
                    return render_template("change_pw.html", form=form, email=form.email.data, temp_password_required=True)
                if form.remember_me.data:
                    login_user(user, remember=True)
                    print("Remember me!!!!!!!!!!!")
                else:
                    login_user(user)
                    print("Don't remember me!!!!!!!!! " + str(form.remember_me.data))
                    #testkommentar
                    #testkommentar
                return redirect(url_for("wishlist.index"))
            else:
                flash("Feil passord")
            
        else: 
            flash("Feil brukernavn eller passord")
    #else:
    #    flash("Det oppstod en feil, prøv igjen (LoginForm not validated).")
    return redirect(url_for("auth.login"))


@auth_bp.route("/api/change-pw", methods=["POST"])
def change_pw():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                if len(form.new_password.data) >= 8:
                    login_user(user)
                    hashed_password = bcrypt.generate_password_hash(form.new_password.data)
                    user.password = hashed_password
                    user.force_pw_change = 0
                    db.session.commit()
                    return "Passordet ble endret, videresender til forsiden..."
                else:
                    return "Passordet er for kort"
            else:
                return "Gammelt passord er feil"
        else:
            return "Finner ikke bruker"
    else:
        return "Skjema ble ikke validert"


@auth_bp.route("/api/logout", methods=["POST", "GET"])
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
    if form.validate_on_submit():
        email = User.query.filter_by(email=form.email.data).first()
        if email:
            return "E-post allerede registrert."
        username = form.first_name.data.split()[0].casefold() + form.last_name.data[:1].casefold()
        username_query = "1"
        for i in range(10):
            if username_query != "1":
                username = username + str(rand.randint(10, 99))
            username_query = User.query.filter_by(username=username).first()
            if not username_query:
                break
        if username_query:
            return "Det oppstod en feil ved registrering av brukeren"
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(first_name=form.first_name.data.title(),
                        last_name=form.last_name.data.title(),
                        email=form.email.data.casefold(),
                        password=hashed_password,
                        date_of_birth=form.date_of_birth.data,
                        username=username)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("auth.login"))
    return "Noe gikk galt, registreringen ble ikke fullført"


@auth_bp.post("/api/settings/order_by")
@login_required
def set_order_by():
    from app.wishlist.controllers import get_users_ordered_by_settings
    user = db.session.get(User, current_user.id)
    order_by_value = request.form["order_by"]
    if not order_by_value in ["birthday", "first_name"]:
        abort(400)
    user.preferences.order_users_by = order_by_value
    users = [{"first_name": u.first_name, "path": url_for('wishlist.user', user_id=u.id)} for u in get_users_ordered_by_settings()]
    try:
        db.session.commit()
        return jsonify(users)
    except SQLAlchemyError as e:
        return abort(400)


@auth_bp.get("/auth/reset-password")
@login_required
def forgot_password():
    if current_user.id != 1:
        abort(401)
    users = db.session.execute(db.select(User.first_name, User.id)).mappings()
    
    return render_template("reset-password.html", users=users)


@auth_bp.post("/api/reset-password/")
@login_required
def restet_password():
    if current_user.id != 1:
        abort(401)
    
    user = db.session.get(User, request.form["user_id"])
    temp_password = generate_unique_code()
    hashed_password = bcrypt.generate_password_hash(temp_password)
    user.password = hashed_password
    user.force_pw_change = 1
    db.session.commit()

    return {"first_name": user.first_name, "password": temp_password}


# @auth_bp.get("/bytt-passord/<token>")
# def user_reset_password(token):
#     error_message = render_template("change_pw_error.html", message="Beklager, men det ser ut til at lenken du prøver å bruke enten er feil eller ikke er gyldig lenger. Vennligst kontroller at du har riktig lenke.")
#     try:
#         token_id, token_string = token.split("-")
#     except ValueError:
#         return error_message
    
#     token_entry = db.session.get(PasswordResetToken, token_id)
#     if token_entry is not None and token_entry.expires_at > datetime.utcnow() and not token_entry.used_at:
#         name = request.args["name"] if "name" in request.args else None
#         if current_user.is_authenticated and current_user.id != token_entry.user.id:
#             return render_template("change_pw_error.html", message=f"Beklager, men det ser ut til at du prøver å endre passordet til en annen bruker enn den som er logget inn. Vennligst <a href='{url_for('auth.logout_api', token= token_id+'-'+token_string, name=name)}' class='blue-text'>logg ut</a> av den gjeldende brukerkontoen før du forsøker å endre passordet.")
        
#         if bcrypt.check_password_hash(token_entry.token, token_string):
#             form = LoginForm()
#             return render_template("change_pw.html", form=form, name=name)
    
#     return error_message

def token_required(view_function):
    @wraps(view_function)
    def decorated_function(token, *args, **kwargs):
        if token:
            token_id, token_string = extract_token_data(token)
            token_entry = get_password_reset_token_entry(token_id)
            
            if is_valid_token(token_entry, token_string):
                return view_function(token_entry, *args, **kwargs)
            
        error_message = get_error_message("Beklager, men det ser ut til at lenken du prøver å bruke enten er feil eller ikke er gyldig lenger. Vennligst kontroller at du har riktig lenke.")
        return error_message
    return decorated_function



@auth_bp.get("/bytt-passord/<token>")
@token_required
def user_reset_password(token_entry):
    name = request.args.get("name")
    return handle_valid_token(token_entry, name)


def get_error_message(message):
    return render_template("change_pw_error.html", message=message)

def extract_token_data(token):
    try:
        token_id, token_string = token.split("-")
        return token_id, token_string
    except ValueError:
        return None, None

def get_password_reset_token_entry(token_id):
    return db.session.get(PasswordResetToken, token_id)

def is_valid_token(token_entry, token_string):
    return (
        token_entry is not None 
        and token_entry.expires_at > datetime.utcnow() 
        and not token_entry.used_at 
        and bcrypt.check_password_hash(token_entry.token, token_string)
    )

def handle_valid_token(token_entry, name):
    if current_user.is_authenticated and current_user.id != token_entry.user.id:
        logout_url = url_for("auth.logout_api", token=f"{token_entry.id}-{token_entry.token}", name=name)
        return render_template("change_pw_error.html", message=f"Beklager, men det ser ut til at du prøver å endre passordet til en annen bruker enn den som er logget inn. Vennligst <a href='{logout_url}' class='blue-text'>logg ut</a> av den gjeldende brukerkontoen før du forsøker å endre passordet.")
    
    form = ChangePasswordForm()
    return render_template("change_pw.html", form=form, name=name)


@auth_bp.post("/bytt-passord/<token>")
@token_required
def user_change_password(token_entry):
    print("red onion")
    form = ChangePasswordForm()
    name = request.args.get("name")

    if form.validate_on_submit():
        user = token_entry.user
        new_password = form.new_password.data
        hashed_password = bcrypt.generate_password_hash(new_password)
        user.password = hashed_password
        user.force_pw_change = 0
        token_entry.used_at = datetime.utcnow()
        db.session.commit()
        flash("Passordet ble endret, vennligst logg inn på nytt.")
        return redirect(url_for("auth.login"))

    else:
        return render_template("change_pw.html", form=form, name=name)