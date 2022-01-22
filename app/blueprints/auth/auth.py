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
                login_user(user)
                return redirect(url_for("index"))
    return "Noe gikk galt, du ble ikke logget inn"


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@auth_bp.route("/register", methods=["POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(first_name=form.first_name.data, last_name=form.last_name.data, email=form.email.data,
                        password=hashed_password, date_of_birth=form.date_of_birth.data)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))
    return "Noe gikk galt, registreringen ble ikke fullført"
