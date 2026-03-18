# TODO: This file is 300+ lines. Consider splitting into separate modules: wish CRUD, list management, prisjakt integration, JSON serialization.
import os
import logging
from datetime import datetime, timezone

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    flash,
    abort,
    Response,
)
from flask_login import current_user
from sqlalchemy import or_, desc
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import SQLAlchemyError
from urllib.parse import urlsplit

from app import db, api_login_required
from app.forms import WishForm, AjaxForm, WishListForm
from app.auth.models import User
from app.wishlist.models import (
    Wish,
    CoWishUser,
    ClaimedWish,
)  # , WishList, wishes_in_list

APP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(APP_PATH, "templates/wishlist")

api_bp = Blueprint(
    "api", __name__, template_folder=TEMPLATE_PATH, url_prefix="/api"
)  # static_folder='static/views'


# TODO: Finn et bedre navn på ruta
# TODO: Ikke returner valgte navn
# TODO: Verifiser at det ikke er duplikater
@api_bp.route("/typeahead", methods=["GET", "POST"])
@api_login_required
def typeahead():
    searchform = AjaxForm()
    if request.method == "POST":
        if searchform.validate():
            searchbox = searchform.searchbox.data
            result = (
                db.session.execute(
                    db.select(User).where(User.username.like(searchbox + "%")).limit(5)
                )
                .scalars()
                .all()
            )
            return jsonify([e.tojson() for e in result])
    return jsonify([]), 200


@api_bp.post("/add")
@api_login_required
def add():
    form = WishForm()
    if form.validate():
        if not form.wish_img_url.data or len(form.wish_img_url.data) < 5:
            form.wish_img_url.data = url_for("static", filename="gift-default.png")
        try:
            new_wish = Wish(
                user_id=current_user.id,
                title=form.wish_title.data,
                description=form.wish_description.data,
                quantity=form.quantity.data,
                url=form.wish_url.data,
                img_url=form.wish_img_url.data,
                desired=form.desired.data,
                price=form.price.data,
            )

            # request_list_ids = request.form.getlist("lists[]", type=int)
            active_lists = []  # WishList.get_active_lists_from_ids(request_list_ids)

            for wish_list in active_lists:
                wish_list.wishes.append(new_wish)

        except SQLAlchemyError:
            return "Wish model creation failed", 400

        if new_wish:
            try:
                flash("Ønsket ble lagt til")
                db.session.add(new_wish)
                db.session.commit()
            except SQLAlchemyError:
                flash("Det oppstod en feil, gi Daniel beskjed")
                return "Det oppstod en feil ved oppretting av ønsket", 500

            if form.co_wisher.data:
                for co_user_id in form.co_wisher.data.split(","):
                    co_user_id = co_user_id.strip()
                    if co_user_id:
                        new_co_wisher = CoWishUser(
                            id=new_wish.id, co_wish_user_id=co_user_id
                        )
                        db.session.add(new_co_wisher)
                db.session.commit()

            return jsonify({"success": True}), 200, {"ContentType": "application/json"}
    return "Form did not validate", 400


# TODO: Ikke ta i mot GET, håndter alt i ajax så bruker ikke ser denne ruta
@api_bp.post("/update")
@api_login_required
def update():
    wishform = WishForm()

    if wishform.validate() and wishform.edit_id.data:
        wish = db.session.get(Wish, wishform.edit_id.data)

        if wish is None or wish.deleted_at is not None:
            return "Noe gikk galt med oppdatering av ønske", 400

        if wish.user_id == current_user.id:
            if wishform.wish_url.data != wish.url and wish.reported_link:
                db.session.delete(wish.reported_link)

            wish.title = wishform.wish_title.data
            wish.description = wishform.wish_description.data
            wish.quantity = wishform.quantity.data
            wish.url = wishform.wish_url.data
            wish.price = wishform.price.data

            if not wish.img_url or len(wish.img_url) < 5:
                wish.img_url = url_for("static", filename="gift-default.png")
            else:
                wish.img_url = wishform.wish_img_url.data
            wish.desired = 1 if wishform.desired.data else 0

            db.session.execute(db.delete(CoWishUser).where(CoWishUser.id == wish.id))
            form_co_wishers = (
                wishform.co_wisher.data.split(",") if wishform.co_wisher.data else []
            )
            for co_user_id in form_co_wishers:
                co_user_id = co_user_id.strip()
                if co_user_id:
                    db.session.add(
                        CoWishUser(id=wishform.edit_id.data, co_wish_user_id=co_user_id)
                    )

            try:
                db.session.commit()
            except Exception as error:
                db.session.rollback()
                logging.error(f"Error updating wish {wish.id}: {error}")
                return "Det oppstod en feil med oppdatering av ønsket", 500

            referrer = request.referrer
            return (
                redirect(referrer) if referrer else redirect(url_for("wishlist.index"))
            )
    return "Noe gikk galt med oppdatering av ønske", 400


@api_bp.get("/delete")
@api_login_required
def delete_prompt():
    return render_template(
        "/wishlist/modal/action_confirmation.html",
        title="Slette ønske?",
        message="Dette vil slette ønsket ditt for godt",
        buttons="confirm",
    )


@api_bp.delete("/delete")
@api_login_required
def delete():
    wish_id = request.values.get("id")
    if not wish_id:
        return render_template(
            "/wishlist/modal/action_confirmation.html",
            title="Oisann",
            message="Det oppstod en feil, prøv igjen kanskje?",
            buttons="close",
        )
    wish = db.session.get(Wish, int(wish_id))
    if wish is None:
        abort(404)
    if True:
        if wish.user_id == current_user.id:
            wish.deleted_at = datetime.now(timezone.utc)

            try:
                db.session.commit()
                return render_template(
                    "/wishlist/modal/action_confirmation.html",
                    img=url_for(
                        "static",
                        filename="img/great-success/very-nice-great-success.jpg",
                    ),
                    img_alt="Borat saying 'VERY NICE - GREAT SUCCESS'",
                    buttons="close",
                    close_all=True,
                )

            except SQLAlchemyError as e:
                db.session.rollback()
                logging.error(f"Error deleting wish: {e}")
                return render_template(
                    "/wishlist/modal/action_confirmation.html",
                    title="Oisann",
                    message="Kunne ikke slette ønsket akkurat nå. Prøv igjen senere.",
                    buttons="close",
                )
        else:
            return render_template(
                "/wishlist/modal/action_confirmation.html",
                title="Oisann",
                message="Du har ikke rettigheter til å slette dette ønsket.",
                buttons="close",
            )

    return render_template(
        "/wishlist/modal/action_confirmation.html",
        title="Oisann",
        message="Det oppstod en feil, prøv igjen kanskje?",
        buttons="close",
    )


@api_bp.post("/claim")
@api_login_required
def claim():
    form = AjaxForm()
    if form.validate():
        wish = db.session.get(Wish, form.claimed_wish_id.data)
        if wish is None:
            abort(404)
        if not wish.claims and wish.user_id != current_user.id:
            claim = ClaimedWish(
                wish_id=form.claimed_wish_id.data, user_id=current_user.id, quantity=1
            )
            db.session.add(claim)
        elif wish.is_claimed_by_user(current_user.id):
            db.session.execute(
                db.delete(ClaimedWish).where(
                    (ClaimedWish.user_id == current_user.id)
                    & (ClaimedWish.wish_id == wish.id)
                )
            )
        else:
            return "Feil ved claiming", 400

        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Error when claiming wish: {e}")
            return "Det oppstod en feil med å ta ønsket.", 500

        referrer = request.referrer
        return redirect(referrer) if referrer else redirect(url_for("wishlist.index"))


@api_bp.post("/wish/all")
@api_login_required
def wish_mobile():
    wishes = (
        db.session.execute(
            db.select(Wish)
            .options(
                joinedload(Wish.user),
                selectinload(Wish.claims),
                selectinload(Wish.co_wishers).joinedload(CoWishUser.user),
            )
            .where(
                Wish.user_id != current_user.id,
                Wish.deleted_at.is_(None),
                Wish.archived_at.is_(None),
            )
            .order_by(desc(Wish.date_created), desc(Wish.desired))
            .limit(30)
        )
        .scalars()
        .all()
    )
    return wishes_to_json(wishes)


@api_bp.get("/wish/all2")
@api_login_required
def wish_mobile2():
    wishes = db.session.execute(
        db.select(Wish)
        .where(
            Wish.user_id != current_user.id,
            Wish.deleted_at.is_(None),
            Wish.archived_at.is_(None),
        )
        .order_by(desc(Wish.date_created), desc(Wish.desired))
    ).scalars()
    wishes_json = {}
    for wish in wishes:
        wishes_json[wish.id] = {"title": wish.title}
        break

    return "ok"  # wishes_json


@api_bp.post("/wish/claimed")
@api_login_required
def claimed():
    form = AjaxForm()
    wishes = []
    if form.validate():
        wishes = (
            db.session.execute(
                db.select(Wish)
                .options(
                    joinedload(Wish.user),
                    selectinload(Wish.claims),
                    selectinload(Wish.co_wishers).joinedload(CoWishUser.user),
                )
                .where(
                    Wish.claims.any(ClaimedWish.user_id == current_user.id),
                    Wish.deleted_at.is_(None),
                    Wish.archived_at.is_(None),
                )
            )
            .scalars()
            .all()
        )
    return wishes_to_json(wishes)


# TODO: Legg til mulighet for å fjerne seg selv som co wisher
# TODO: Ha separat "ønsker meg mest" for co wishere
# TODO: Bestem redigeringsrettigheter/sletterettigheter for co wisher
@api_bp.post("/wish/user/<int:user_id>")
@api_login_required
def return_user_wishes(user_id):
    form = AjaxForm()
    if not form.validate():
        return jsonify({"error": "Invalid request"}), 400

    order_by = request.values.get("order_by", "")

    order_map = {
        "price_high_low": [Wish.price.desc()],
        "price_low_high": [Wish.price.asc()],
    }
    ordering = order_map.get(order_by) or [
        Wish.desired.desc(),
        Wish.date_created.desc(),
    ]

    base_filter = or_(
        Wish.user_id == user_id,
        Wish.co_wishers.any(CoWishUser.co_wish_user_id == user_id),
    )

    wishes = (
        db.session.execute(
            db.select(Wish)
            .where(base_filter, Wish.deleted_at.is_(None), Wish.archived_at.is_(None))
            .order_by(*ordering)
        )
        .scalars()
        .all()
    )

    return wishes_to_json(wishes)


@api_bp.post("/wish/new")
@api_login_required
def new_wish():
    wish_form = WishForm()
    claim_form = AjaxForm()
    empty_wish = Wish(
        user_id="",
        title="",
        description="",
        url="",
        img_url=url_for("static", filename="gift-default.png"),
        desired="",
    )

    lists = None  # WishList.get_active_lists(current_user.id)

    return render_template(
        "wishlist/modal/wish_modal_edit_content.html",
        wish=empty_wish,
        wish_form=wish_form,
        claimform=claim_form,
        form_action="add",
        lists=lists,
    )


@api_bp.get("/wish/<int:wish_id>")
@api_login_required
def return_modal(wish_id):
    claim_form = AjaxForm()
    wish = db.session.get(Wish, wish_id)
    if wish is None or wish.deleted_at is not None:
        abort(404)

    # Returnere redigerbart ønske
    if wish.user_id == current_user.id:
        wish_form = WishForm(quantity=wish.quantity)
        lists = None  # WishList.get_active_lists(current_user.id)
        return render_template(
            "wishlist/modal/wish_modal_edit_content.html",
            wish=wish,
            claimform=claim_form,
            wish_form=wish_form,
            form_action="update",
            lists=lists,
        )
    # Returnere andres ønske
    else:
        netloc = "{0.netloc}".format(urlsplit(wish.url))
        return render_template(
            "wishlist/modal/wish_modal_view_content.html",
            wish=wish,
            claimform=claim_form,
            netloc=netloc,
        )
    # else:
    #    return "getwishesform didn't validate"


# FIXME: Tullete å kalle denne for hver bruker som blir lagt i lista
@api_bp.post("/cowisher")
@api_login_required
def cowisher():
    user_id = db.session.get(User, request.values.get("user_id"))
    if user_id:
        return jsonify(success=True)
    else:
        return "Record not found", 400


def wishes_to_json(wishes):
    # TODO: N+1 query problem — each wish accesses whs.user.first_name, whs.get_co_wishers(), etc. via lazy loading.
    #   Use joinedload/selectinload in the calling queries to eager-load relationships.
    wishes_json_string = []
    show_claims = (
        current_user.preferences.show_claims if current_user.preferences else True
    )
    for whs in wishes:
        wishes_json_string.append(
            {
                "id": whs.id,
                "claimed": True
                if whs.claims and whs.user_id != current_user.id and show_claims
                else False,
                "img_url": whs.img_url,
                "first_name": whs.user.first_name,
                "co_wisher": whs.get_co_wishers(),
                "age": whs.time_since_creation(),
                "title": whs.title,
                "price": f"{whs.price:,}".replace(",", " ") if whs.price else "",
                "desired": whs.desired,
                "base_url": "{0.netloc}".format(urlsplit(whs.url)),
                "url": whs.url,
            }
        )
    if wishes_json_string:
        return jsonify(wishes_json_string)
    else:
        return jsonify({}), 200, {"ContentType": "application/json"}


@api_bp.post("/prisjakt")
@api_login_required
def prisjakt():
    json_data = request.get_json() or {}
    product_code = json_data.get("product_code")
    if not product_code:
        abort(400)

    from .prisjakt import make_request

    response = make_request(product_code)

    if response.status_code == 404:
        abort(404)

    if response.status_code != 200:
        return Response(response.text, status=500)

    try:
        response_data = response.json()
        product_name = response_data["items"][0]["name"]
        product_price = response_data["items"][0]["price"]["regular"]
        product_image = response_data["items"][0]["media"]["product_images"]["first"]["800"]
    except (KeyError, IndexError, ValueError) as e:
        logging.error(f"Unexpected Prisjakt response structure: {e}")
        abort(404)

    return jsonify(
        {
            "product_name": product_name,
            "product_price": product_price,
            "product_image": product_image,
        }
    )


@api_bp.get("/wish/lists")
@api_login_required
def get_lists_modal_content():
    form = WishListForm()
    title_placeholder = WishListForm.get_title_placeholder()
    lists = None  # WishList.get_active_lists(current_user.id)
    return render_template(
        "wishlist/modal/user_lists_modal.html",
        lists=lists,
        form=form,
        title_placeholder=title_placeholder,
    )


""" @api_bp.get("/wish-list/<int:list_id>")
@api_login_required
def get_list_details(list_id):
    abort(500)
    list_obj = db.session.get(WishList, list_id)

    if list_obj.user_id != current_user.id:
        abort(403)

    if not list_obj.is_active():
        abort(410)

    return {
        "title": list_obj.title,
        "expires_at": list_obj.expires_at.strftime("%Y-%m-%d"),
        "private": bool(list_obj.private)
    } """


@api_bp.post("/wish-list/update")
@api_login_required
def update_wish_list():
    return "ok", 200
