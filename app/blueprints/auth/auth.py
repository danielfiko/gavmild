import random as rand
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, login_user, logout_user
from app import db
from app.forms import RegisterForm, LoginForm
from app.models import User
from app import bcrypt

auth_bp = Blueprint("auth", __name__,
                    template_folder='templates',
                    static_folder='static', static_url_path='')


@auth_bp.route("/login", methods=["POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                if user.force_pw_change:
                    return render_template("change_pw.html", form=form, email=form.email.data)
                login_user(user)
                return redirect(url_for("views.index"))
            return "wrong password"
        return "no user"
    return "LoginForm not validated"
    return "Noe gikk galt, du ble ikke logget inn"


@auth_bp.route("/change-pw", methods=["POST"])
def change_pw():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                if len(form.password.data) >= 8:
                    login_user(user)
                    hashed_password = bcrypt.generate_password_hash(form.new_password.data)
                    user.password = hashed_password
                    user.force_pw_change = 0
                    db.session.commit()
                    return redirect(url_for("views.index"))
    return "Noe gikk galt."


@auth_bp.route("/logout", methods=["POST", "GET"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("views.index"))


@auth_bp.route("/register", methods=["POST"])
def register():
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
        return redirect(url_for("views.login"))
    return "Noe gikk galt, registreringen ble ikke fullført"
