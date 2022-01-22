from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.forms import GetWishesForm, ClaimForm, WishForm, RegisterForm, LoginForm
from app import db
from app.models import Wish, User, CoWishUser

views_bp = Blueprint("views", __name__,
                     template_folder='templates/views',
                     static_folder='static/views', url_prefix='/')


@views_bp.route("/")
def index():
    if current_user.is_authenticated:
        get_wishes_form = GetWishesForm()
        claimform = ClaimForm()
        wishform = WishForm()
        return render_template("wishes.html", getform=get_wishes_form, claimform=claimform, wishform=wishform,
                               filter_value="all_but_own")
    else:
        form = LoginForm()
        return render_template("login.html", form=form)


@views_bp.route("/test")
def db_test():
    wish_id = 5
    wish = db.session.query(Wish, User.first_name).join(User, User.id == Wish.user_id).filter(
        Wish.id == wish_id).one()
    co_wisher = db.session.query(User.username, User.id).join(CoWishUser).filter(
        CoWishUser.id == wish_id).all()
    return jsonify(wish)


@views_bp.route("/user/<int:user_id>")
@login_required
def user(user_id):
    get_wishes_form = GetWishesForm()
    wishform = WishForm()
    return render_template("wishes.html", getform=get_wishes_form, wishform=wishform, filter_value="own")


@views_bp.route("/claimed")
@login_required
def claimed():
    get_wishes_form = GetWishesForm()
    claimform = ClaimForm()
    wishform = WishForm()
    return render_template("wishes.html", getform=get_wishes_form, claimform=claimform, wishform=wishform,
                           filter_value="claimed")


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