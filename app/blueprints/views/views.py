from flask import Blueprint, render_template, jsonify, abort
from flask_login import login_required, current_user
from app.forms import WishForm, RegisterForm, LoginForm, AjaxForm
from app import db
from app.models import Wish, User, CoWishUser

views_bp = Blueprint("views", __name__,
                     template_folder='templates/views',
                     static_folder='static/views', url_prefix='/')
other_users = User.query.filter(id != current_user).all()


@views_bp.route("/")
@login_required
def index():
    return logged_in_content("all")


@views_bp.route("/user/<int:user_id>")
@login_required
def user(user_id):
    return logged_in_content("user/"+str(user_id))


def logged_in_content(filter):
    ajaxform = AjaxForm()
    wishform = WishForm()
    return render_template("logged_in_content.html",
                           ajaxform=ajaxform, wishform=wishform, filter=filter, other_users=other_users)


@views_bp.route("/claimed")
@login_required
def claimed():
    return logged_in_content("claimed")


@views_bp.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    return render_template("dashboard.html")


@views_bp.route("/login")
def login():
    form = LoginForm()
    return render_template("login.html", form=form)


@views_bp.route("/register")
def register():
    form = RegisterForm()
    return render_template("register.html", form=form)
