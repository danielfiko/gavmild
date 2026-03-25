from flask import abort, flash, redirect, request, url_for
from flask_login import login_required

from app.admin import admin_bp
from app.admin import controllers
from app.admin.decorators import admin_required
from app.wishlist.controllers import logged_in_content
from app.telegram.controllers import unlink_telegram_user


@admin_bp.get("/")
@login_required
@admin_required
def index():
    return logged_in_content("admin_index.html", page_title="Adminpanel", filter="")


@admin_bp.get("/users")
@login_required
@admin_required
def users():
    all_users = controllers.get_all_users()
    return logged_in_content(
        "admin_users.html",
        page_title="Brukere",
        filter="",
        admin_users=all_users,
    )


@admin_bp.get("/users/<int:user_id>")
@login_required
@admin_required
def user_detail(user_id):
    user = controllers.get_user_details(user_id)
    if user is None:
        abort(404)
    return logged_in_content(
        "admin_user_detail.html",
        page_title=f"{user.first_name} {user.last_name}",
        filter="",
        admin_user=user,
    )


@admin_bp.post("/users/<int:user_id>/update")
@login_required
@admin_required
def user_update(user_id):
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip()
    is_admin = "is_admin" in request.form
    force_pw_change = "force_pw_change" in request.form

    if not first_name or not email:
        flash("Fornavn og e-post er påkrevd.", "error")
        return redirect(url_for("admin.user_detail", user_id=user_id))

    result = controllers.update_user(user_id, first_name, last_name, email, is_admin, force_pw_change)
    if result["ok"]:
        flash("Bruker oppdatert.", "success")
    else:
        flash(result.get("error", "Noe gikk galt."), "error")
    return redirect(url_for("admin.user_detail", user_id=user_id))


@admin_bp.post("/users/<int:user_id>/reset-password")
@login_required
@admin_required
def user_reset_password(user_id):
    result = controllers.generate_reset_link(user_id)
    if result["ok"]:
        flash(result["url"], "reset_url")
    else:
        flash(result.get("error", "Noe gikk galt."), "error")
    return redirect(url_for("admin.user_detail", user_id=user_id))


@admin_bp.get("/suggestions")
@login_required
@admin_required
def suggestions():
    active_filter = request.args.get("filter", "open")
    if active_filter not in {"open", "solved", "all"}:
        active_filter = "open"
    suggestion_list = controllers.get_all_suggestions(filter=active_filter)
    return logged_in_content(
        "admin_suggestions.html",
        page_title="Forslag",
        filter="",
        suggestion_list=suggestion_list,
        active_filter=active_filter,
    )


@admin_bp.post("/suggestions/<int:suggestion_id>/solve")
@login_required
@admin_required
def suggestion_solve(suggestion_id):
    active_filter = request.args.get("filter", "open")
    result = controllers.solve_suggestion(suggestion_id)
    if not result["ok"]:
        flash(result.get("error", "Noe gikk galt."), "error")
    return redirect(url_for("admin.suggestions", filter=active_filter))


@admin_bp.post("/suggestions/<int:suggestion_id>/delete")
@login_required
@admin_required
def suggestion_delete(suggestion_id):
    active_filter = request.args.get("filter", "open")
    result = controllers.delete_suggestion(suggestion_id)
    if not result["ok"]:
        flash(result.get("error", "Noe gikk galt."), "error")
    return redirect(url_for("admin.suggestions", filter=active_filter))


@admin_bp.get("/telegram")
@login_required
@admin_required
def telegram():
    tg_users = controllers.get_all_telegram_users()
    return logged_in_content(
        "admin_telegram.html",
        page_title="Telegram-brukere",
        filter="",
        tg_users=tg_users,
    )


@admin_bp.post("/telegram/<int:telegram_id>/unlink")
@login_required
@admin_required
def telegram_unlink(telegram_id):
    result = unlink_telegram_user(telegram_id)
    if result["ok"]:
        flash("Telegram-bruker koblet fra.", "success")
    else:
        flash(result.get("error", "Noe gikk galt."), "error")
    return redirect(url_for("admin.telegram"))

@admin_bp.get("/msg/<int:user_id>/<string:msg>")
@login_required
@admin_required
def msg(user_id, msg):
    from app.telegram.controllers import telegram_bot_sendtext
    try:
        telegram_bot_sendtext(user_id, msg)
        return "ok"
    except Exception as e:
        return f"Error sending Telegram message to user {user_id}: {e}"