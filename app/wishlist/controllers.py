import calendar
from datetime import datetime, timezone

from flask import render_template, redirect, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy import func, desc, or_
from sqlalchemy.orm import joinedload, selectinload

from app import db
from app.forms import APIform, WishForm, AjaxForm
from app.wishlist import wishlist_bp
from app.auth.models import User
from app.wishlist.models import WishList, Wish, CoWishUser


def calculate_expires_at(
    template: str, user: User, custom_date: datetime | None = None
) -> datetime:
    """Return the expiry datetime for a new list based on the chosen template.

    Raises ValueError if the template is unrecognised or required data is missing.
    """
    now = datetime.now(timezone.utc)

    if template == "christmas":
        candidate = datetime(now.year, 12, 24, tzinfo=timezone.utc)
        if candidate <= now:
            candidate = datetime(now.year + 1, 12, 24, tzinfo=timezone.utc)
        return candidate

    if template == "birthday":
        month = user.date_of_birth.month
        day = user.date_of_birth.day
        # Feb 29 — use Feb 28 when the target year is not a leap year
        for year_offset in range(0, 3):
            year = now.year + year_offset
            if month == 2 and day == 29 and not calendar.isleap(year):
                actual_day = 28
            else:
                actual_day = day
            candidate = datetime(year, month, actual_day, tzinfo=timezone.utc)
            if candidate > now:
                return candidate
        raise ValueError("Could not determine next birthday occurrence")

    if template == "custom":
        if custom_date is None:
            raise ValueError("custom_date is required for the 'custom' template")
        if custom_date.tzinfo is None:
            custom_date = custom_date.replace(tzinfo=timezone.utc)
        return custom_date

    raise ValueError(f"Unknown template: {template!r}")


@wishlist_bp.get("/grid-test")
@login_required
def grid_test():
    user_id = current_user.id
    base_filter = or_(
        Wish.user_id == user_id,
        Wish.co_wishers.any(CoWishUser.co_wish_user_id == user_id),
    )
    wishes = (
        db.session.execute(
            db.select(Wish)
            .options(
                joinedload(Wish.user),
                selectinload(Wish.claims),
                selectinload(Wish.co_wishers).joinedload(CoWishUser.user),
                joinedload(Wish.wish_list),
            )
            .where(
                base_filter,
                Wish.deleted_at.is_(None),
                ~Wish.wish_list.has(WishList.archived_at.isnot(None)),
            )
        )
        .scalars()
        .all()
    )

    return logged_in_content("wishes_grid_test.html", filter="all", wishes=wishes)


@wishlist_bp.route("/")
@wishlist_bp.route("/wish/<int:wish_id>")
def index(wish_id=0):
    if current_user.is_authenticated:
        return logged_in_content("wish_content.html", filter="all")
    else:
        return redirect(url_for("auth.login"))


@wishlist_bp.route("/user/<int:user_id>")
@wishlist_bp.route("/user/<int:user_id>/wish/<int:wish_id>")
@login_required
def user(user_id, wish_id=0):
    return get_user_page(user_id)


def get_users_ordered_by_settings():
    if (
        current_user.preferences is not None
        and current_user.preferences.order_users_by == "birthday"
    ):
        # Get users by upcoming birthdays
        today = datetime.today()
        users = db.session.execute(
            db.select(
                User,
                func.dayofyear(User.date_of_birth) - func.dayofyear(today),
                func.dayofyear(User.date_of_birth) >= func.dayofyear(today),
            ).order_by(
                desc(func.dayofyear(User.date_of_birth) >= func.dayofyear(today)),
                func.dayofyear(User.date_of_birth) - func.dayofyear(today),
            )
        ).scalars()
        return users

    users = db.session.execute(db.select(User).order_by(User.first_name)).scalars()
    return users


@wishlist_bp.get("/report-dead-link/<int:wish_id>")
@login_required
def get_report_dead_link_modal(wish_id):
    wish = db.session.get(Wish, wish_id)
    if wish is None:
        abort(404)

    return render_template(
        "/wishlist/modal/action_confirmation.html",
        title="Rapporter død lenke?",
        message=f"Det blir sendt en melding til {wish.user.first_name} om at lenken ikke fungerer.",
        buttons="confirm",
    )


def get_user_page(user_id):
    page_title = None
    target_user = db.session.get(User, user_id)
    if target_user is None:
        abort(404)
    if user_id != current_user.id:
        page_title = target_user.first_name + "s ønskeliste"
    else:
        page_title = "Min ønskeliste"

    target_user_lists = (
        db.session.execute(
            db.select(WishList)
            .where(WishList.user_id == user_id, WishList.archived_at.is_(None))
            .order_by(WishList.created_at.desc())
        )
        .scalars()
        .all()
    )

    return logged_in_content(
        "wish_content.html",
        page_title=page_title,
        filter=f"user/{user_id}",
        lists=target_user_lists,
    )


def logged_in_content(
    template_name, **kwargs
):  # TODO: Flytt form-variablene dit de hører hjemme
    # TODO: PERFORMANCE - This loads ALL users, ALL birthdays, and creates multiple form instances on every single page load.
    #   Consider caching, lazy loading, or only loading what's needed per page.
    users = get_users_ordered_by_settings()
    order_by = (
        current_user.preferences.order_users_by if current_user.preferences else None
    )
    birthdays = User.upcoming_birthdays()
    ajaxform = AjaxForm()
    wishform = WishForm()
    api_form = APIform()
    lists = kwargs.pop("lists", [])

    return render_template(
        template_name,
        users=users,
        order_by=order_by,
        birthdays=birthdays,
        ajaxform=ajaxform,
        wishform=wishform,
        api_form=api_form,
        lists=lists,
        **kwargs,
    )


@wishlist_bp.route("/claimed")
@login_required
def claimed():
    return logged_in_content(
        "wish_content.html",
        page_title="Ønsker jeg har tatt",
        filter="claimed",
    )


@wishlist_bp.get("/arkiverte-lister")
@login_required
def archived_lists():
    return logged_in_content(
        "archived_lists.html",
        page_title="Arkiverte lister",
    )
