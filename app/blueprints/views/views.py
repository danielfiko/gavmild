from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.forms import GetWishesForm, ClaimForm, WishForm, RegisterForm, LoginForm
from app import db
from app.models import Wish, User, CoWishUser

views_bp = Blueprint("views", __name__,
                     template_folder='templates/views',
                     static_folder='static/views', url_prefix='/')
other_users = User.query.filter(id != current_user).all()


@views_bp.route("/")
def index():
    if current_user.is_authenticated:
        get_wishes_form = GetWishesForm()
        claimform = ClaimForm()
        wishform = WishForm()
        return render_template("wishes.html", getform=get_wishes_form, claimform=claimform, wishform=wishform,
                               filter_value="all", other_users=other_users)
    else:
        form = LoginForm()
        return render_template("login.html", form=form)


@views_bp.route("/user/<int:user_id>")
@login_required
def user(user_id):
    get_wishes_form = GetWishesForm()
    wishform = WishForm()
    return render_template("wishes.html", getform=get_wishes_form, wishform=wishform, filter_value="user/"+str(user_id),
                           other_users=other_users)


@views_bp.route("/claimed")
@login_required
def claimed():
    get_wishes_form = GetWishesForm()
    claimform = ClaimForm()
    wishform = WishForm()
    return render_template("wishes.html", getform=get_wishes_form, claimform=claimform, wishform=wishform,
                           filter_value="claimed", other_users=other_users)


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