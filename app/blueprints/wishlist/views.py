from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.blueprints.auth.models import User
from sqlalchemy import func
from app.forms import WishForm, AjaxForm
from app.database.database import db


wishlist_bp = Blueprint('wishlist', __name__, template_folder="templates/wishlist", url_prefix='/') # static_folder='static/views'

################


@wishlist_bp.route("/")
def index():
    if current_user.is_authenticated:
        return logged_in_content("all")
    else:
        return redirect(url_for("auth.login"))


@wishlist_bp.route("/user/<int:user_id>")
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
    start = datetime.now()
    end = start + timedelta(days=60)
    users = db.session.execute(db.select(User).where(User.date_of_birth <= end).where(User.date_of_birth >= start)).scalars()
    birthdays = [{"id": u.id, "first_name": u.first_name,
                  "birthday": f"{u.date_of_birth.day}. {months[u.date_of_birth.month]}"} for u in users]
    ajaxform = AjaxForm()
    wishform = WishForm()
    return render_template("logged_in_content.html",
                           ajaxform=ajaxform, wishform=wishform, filter=page_filter, other_users=other_users,
                           birthdays=birthdays, page_title=page_title)


@wishlist_bp.route("/claimed")
@login_required
def claimed():
    return logged_in_content("claimed")