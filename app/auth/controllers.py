from flask import Blueprint, render_template, redirect, url_for, flash, abort, jsonify, request
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from app.forms import RegisterForm, LoginForm
#from app.blueprints.auth.models import User
import random as rand
from app.database.database import db
from app.auth.models import User
from app.telegram.models import TelegramUser
import os
from sqlalchemy.exc import SQLAlchemyError


APP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(APP_PATH, 'templates/auth')

login_manager = LoginManager()
login_manager.login_view = "auth.login"
bcrypt = Bcrypt()


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
                    return render_template("change_pw.html", form=form, email=form.email.data)
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
    form = LoginForm()
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
    users = [{"first_name": u.first_name, "path": url_for('wishlist.user', user_id=user.id)} for u in get_users_ordered_by_settings()]
    try:
        db.session.commit()
        return jsonify(users)
    except SQLAlchemyError as e:
        return abort(400)