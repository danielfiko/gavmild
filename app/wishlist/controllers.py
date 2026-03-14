from datetime import datetime

from flask import render_template, redirect, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy import func, desc

from app import db
from app.forms import APIform, WishForm, AjaxForm
from app.wishlist import wishlist_bp
from app.auth.models import User


@wishlist_bp.route("/")
@wishlist_bp.route("/wish/<int:wish_id>")
def index(wish_id=0):
    if current_user.is_authenticated:
        return logged_in_content(
            "wish_content.html",
            filter="all")
    else:
        return redirect(url_for("auth.login"))


@wishlist_bp.route("/user/<int:user_id>")
@wishlist_bp.route("/user/<int:user_id>/wish/<int:wish_id>")
@login_required
def user(user_id, wish_id=0):
    return get_user_page(user_id)


def get_users_ordered_by_settings():
    if current_user.preferences is not None and current_user.preferences.order_users_by == "birthday":
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


def get_user_page(user_id):
    page_title = None
    target_user = db.session.get(User, user_id)
    if target_user is None:
        abort(404)
    if user_id != current_user.id:
        page_title = target_user.first_name + "s ønskeliste"
    else:
        page_title = "Min ønskeliste"

    return logged_in_content(
        "wish_content.html",
        page_title=page_title,
        filter=f"user/{user_id}",
    )


def logged_in_content(template_name, **kwargs):  # TODO: Flytt form-variablene dit de hører hjemme
    # TODO: PERFORMANCE - This loads ALL users, ALL birthdays, and creates multiple form instances on every single page load.
    #   Consider caching, lazy loading, or only loading what's needed per page.
    users = get_users_ordered_by_settings()
    order_by = current_user.preferences.order_users_by if current_user.preferences else None
    birthdays = User.upcoming_birthdays()
    ajaxform = AjaxForm()
    wishform = WishForm()
    api_form = APIform()
    lists = []  # WishList.get_active_lists(user_id)

    return render_template(template_name,
                           users=users,
                           order_by=order_by,
                           birthdays=birthdays,
                           ajaxform=ajaxform,
                           wishform=wishform,
                           api_form=api_form,
                           lists=lists,
                           **kwargs)


@wishlist_bp.route("/claimed")
@login_required
def claimed():
    return logged_in_content(
        "wish_content.html",
        page_title="Ønsker jeg har tatt",
        filter="claimed",
    )
