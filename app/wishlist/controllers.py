from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from app.forms import APIform, WishForm, AjaxForm
from app.database.database import db
from app.auth.models import User
import os

APP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(APP_PATH, 'templates/wishlist')
wishlist_bp = Blueprint('wishlist', __name__, template_folder=TEMPLATE_PATH, url_prefix='/') # static_folder='static/views'

################

@wishlist_bp.route("/")
@wishlist_bp.route("/wish/<int:wish_id>")
def index(wish_id=0):
    if current_user.is_authenticated:
        return logged_in_content("all")
    else:
        return redirect(url_for("auth.login"))


@wishlist_bp.route("/user/<int:user_id>")
@wishlist_bp.route("/user/<int:user_id>/wish/<int:wish_id>")
@login_required
def user(user_id,wish_id=0):
    return logged_in_content("user/" + str(user_id))


def get_users_ordered_by_settings():
    if current_user.preferences:
        if current_user.preferences.order_users_by == "birthday":
            # Get users by upcoming birthdays
            today = datetime.today()
            users = db.session.execute(db.select(
                User, 
                func.dayofyear(User.date_of_birth) - func.dayofyear(today),
                func.dayofyear(User.date_of_birth) >= func.dayofyear(today)
            ).order_by(
                desc(func.dayofyear(User.date_of_birth) >= func.dayofyear(today)),
                func.dayofyear(User.date_of_birth) - func.dayofyear(today),
            )).scalars()
            return users
    
    users = db.session.execute(db.select(User).order_by(User.first_name)).scalars()
    return users


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
    #other_users = User.query.filter(id != current_user).all()

    other_users = get_users_ordered_by_settings()

    # Get users with birthday next 60 days
    start = datetime.now()
    end = start + timedelta(days=60)
    user_birthdays = db.session.execute(
        db.select(User)
        .where(func.dayofyear(User.date_of_birth) >= func.dayofyear(start))
        .where(func.dayofyear(User.date_of_birth) <= func.dayofyear(end))
        .order_by(func.dayofyear(User.date_of_birth))
        ).scalars()
    birthdays = [{"id": u.id, "first_name": u.first_name,
                  "birthday": f"{u.date_of_birth.day}. {months[u.date_of_birth.month]}"} for u in user_birthdays]
    ajaxform = AjaxForm()
    wishform = WishForm()
    api_form = APIform()
    order_by = current_user.preferences.order_users_by
    
    return render_template("logged_in_content.html",
                           ajaxform=ajaxform, wishform=wishform, filter=page_filter, other_users=other_users,
                           birthdays=birthdays, page_title=page_title, api_form=api_form, order_by=order_by)


@wishlist_bp.route("/claimed")
@login_required
def claimed():
    return logged_in_content("claimed")
