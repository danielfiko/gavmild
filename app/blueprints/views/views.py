from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func

from app.forms import WishForm, RegisterForm, LoginForm, AjaxForm
from app.models import User

views_bp = Blueprint("views", __name__,
                     template_folder='templates/views',
                     static_folder='static/views', url_prefix='/')


@views_bp.route("/")
@login_required
def index():
    return logged_in_content("all")


@views_bp.route("/user/<int:user_id>")
@login_required
def user(user_id):
    return logged_in_content("user/" + str(user_id))


def logged_in_content(page_filter):
    page_title = ""
    if page_filter[:5] == "user/":
        if int(page_filter.split("/")[1]) != current_user.id:
            page_title = User.query.get(int(page_filter.split("/")[1])).first_name + "s ønskeliste"
        else:
            page_title = "Min ønskeliste"
    elif page_filter == "claimed":
        page_title = "Ønsker jeg har tatt"
    months = {1: "jan.", 2: "feb.", 3: "mar.", 4: "apr.", 5: "mai", 6: "jun.", 7: "jul.", 8: "aug.", 9: "sep.",
              10: "okt.", 11: "nov.", 12: "des."}
    other_users = User.query.filter(id != current_user).all()
    users = User.query.filter(func.strftime("%j", User.date_of_birth) - func.strftime("%j", "now") < 60) \
        .filter(func.strftime("%j", User.date_of_birth) > func.strftime("%j", "now", "-1 days")).all()
    birthdays = [{"id": u.id, "first_name": u.first_name,
                  "birthday": f"{u.date_of_birth.day}. {months[u.date_of_birth.month]}"} for u in users]
    ajaxform = AjaxForm()
    wishform = WishForm()
    return render_template("logged_in_content.html",
                           ajaxform=ajaxform, wishform=wishform, filter=page_filter, other_users=other_users,
                           birthdays=birthdays, page_title=page_title)


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


@views_bp.route("/superhemmelig-lag-konto-side")
def register():
    form = RegisterForm()
    return render_template("register.html", form=form)