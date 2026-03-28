# TODO: This file is 300+ lines. Consider splitting into separate modules: wish CRUD, list management, prisjakt integration, JSON serialization.
import logging
import os
from datetime import datetime, timezone
from urllib.parse import urlsplit

from flask import (
    Blueprint,
    Response,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user
from sqlalchemy import desc, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload

from app import api_login_required, db
from app.auth.models import User
from app.forms import AjaxForm, WishForm, WishListForm
from app.wishlist.controllers import calculate_expires_at
from app.wishlist.models import (
    ClaimedWish,
    CoWishUser,
    Wish,
    WishList,
)

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
    lists = (
        db.session.execute(
            db.select(WishList)
            .where(WishList.user_id == current_user.id, WishList.archived_at.is_(None))
            .order_by(WishList.created_at.desc())
        )
        .scalars()
        .all()
    )
    form.list_id.choices = [(lst.id, lst.title) for lst in lists]
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
                list_id=form.list_id.data,
            )

            # request_list_ids = request.form.getlist("lists[]", type=int)
            active_lists = []  # WishList.get_active_lists_from_ids(request_list_ids)

            for wish_list in active_lists:
                wish_list.wishes.append(new_wish)

        except SQLAlchemyError:
            return "Wish model creation failed", 400

        if new_wish:
            try:
                db.session.add(new_wish)
                db.session.commit()
            except SQLAlchemyError:
                return "Det oppstod en feil, gi Daniel beskjed", 500

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
    lists = (
        db.session.execute(
            db.select(WishList)
            .where(WishList.user_id == current_user.id, WishList.archived_at.is_(None))
            .order_by(WishList.created_at.desc())
        )
        .scalars()
        .all()
    )
    wishform.list_id.choices = [(lst.id, lst.title) for lst in lists]

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
            wish.list_id = wishform.list_id.data or None

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
    logging.warning(f"Wish update failed validation: {wishform.errors}")
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


@api_bp.delete("/delete/<int:wish_id>")
@api_login_required
def delete(wish_id):
    wish = None
    if wish_id:
        wish = db.session.get(Wish, int(wish_id))

    if not wish:
        return render_template(
            "/wishlist/modal/action_confirmation.html",
            title="Oisann",
            message="Det oppstod en feil, prøv igjen kanskje?",
            buttons="close",
        )

    if wish.user_id != current_user.id:
        return render_template(
            "/wishlist/modal/action_confirmation.html",
            title="Oisann",
            message="Du har ikke rettigheter til å slette dette ønsket.",
            buttons="close",
        )

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


@api_bp.post("/claim")
@api_login_required
def claim():
    form = AjaxForm()
    if form.validate():
        wish = db.session.get(Wish, form.claimed_wish_id.data)
        if wish is None:
            abort(404)
        if wish.list_id is not None:
            wish_list = db.session.get(WishList, wish.list_id)
            if wish_list is not None and wish_list.archived_at is not None:
                return jsonify(
                    {"error": "Denne listen er arkivert og kan ikke endres."}
                ), 409
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
                joinedload(Wish.wish_list),
            )
            .where(
                Wish.user_id != current_user.id,
                Wish.deleted_at.is_(None),
                ~Wish.wish_list.has(WishList.archived_at.isnot(None)),
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
            ~Wish.wish_list.has(WishList.archived_at.isnot(None)),
        )
        .order_by(desc(Wish.date_created), desc(Wish.desired))
    ).scalars()
    wishes_json = {}
    for wish in wishes:
        wishes_json[wish.id] = {"title": wish.title}
        break

    return "ok"


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
                    joinedload(Wish.wish_list),
                )
                .where(
                    Wish.claims.any(ClaimedWish.user_id == current_user.id),
                    Wish.deleted_at.is_(None),
                    ~Wish.wish_list.has(WishList.archived_at.isnot(None)),
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
            .order_by(*ordering)
        )
        .scalars()
        .all()
    )

    return wishes_to_json(wishes)


@api_bp.get("/wish/new")
@api_login_required
def new_wish():
    wish_form = WishForm()
    claim_form = AjaxForm()
    empty_wish = Wish(
        user_id="",
        title="",
        description="",
        url="",
        img_url=url_for("static", filename="img/gift-default.png"),
        desired="",
    )

    lists = (
        db.session.execute(
            db.select(WishList)
            .where(WishList.user_id == current_user.id, WishList.archived_at.is_(None))
            .order_by(WishList.created_at.desc())
        )
        .scalars()
        .all()
    )  # WishList.get_active_lists(current_user.id)
    wish_form.list_id.choices = [(lst.id, lst.title) for lst in lists]

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
        lists = (
            db.session.execute(
                db.select(WishList)
                .where(
                    WishList.user_id == current_user.id,
                    WishList.archived_at.is_(None),
                )
                .order_by(WishList.created_at.desc())
            )
            .scalars()
            .all()
        )  # WishList.get_active_lists(current_user.id)
        wish_form.list_id.choices = [(lst.id, lst.title) for lst in lists]
        wish_form.list_id.data = wish.list_id
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
                "list_id": whs.list_id,
                "list_title": whs.wish_list.title if whs.wish_list else None,
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
        product_image = response_data["items"][0]["media"]["product_images"]["first"][
            "800"
        ]
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
    lists = (
        db.session.execute(
            db.select(WishList)
            .where(WishList.user_id == current_user.id, WishList.archived_at.is_(None))
            .order_by(WishList.created_at.desc())
        )
        .scalars()
        .all()
    )
    return render_template(
        "wishlist/modal/user_lists_modal.html",
        lists=lists,
        form=form,
        title_placeholder=title_placeholder,
    )


@api_bp.get("/wishes/<int:wish_id>/move-modal")
@api_login_required
def move_modal_content(wish_id: int):
    """Render the move/copy modal for a wish on an archived list."""
    wish = db.session.get(Wish, wish_id)
    if wish is None or wish.deleted_at is not None:
        abort(404)
    if wish.user_id != current_user.id:
        abort(403)
    if wish.list_id is None:
        abort(400)
    source_list = db.session.get(WishList, wish.list_id)
    if source_list is None or source_list.archived_at is None:
        abort(400)
    active_lists = (
        db.session.execute(
            db.select(WishList)
            .where(WishList.user_id == current_user.id, WishList.archived_at.is_(None))
            .order_by(WishList.created_at.desc())
        )
        .scalars()
        .all()
    )
    return render_template(
        "wishlist/modal/move_modal.html",
        wish=wish,
        active_lists=active_lists,
    )


@api_bp.get("/lists")
@api_login_required
def get_user_lists():
    """Return all active and archived lists for the current user."""
    rows = (
        db.session.execute(
            db.select(WishList)
            .where(WishList.user_id == current_user.id)
            .order_by(WishList.archived_at.is_(None).desc(), WishList.expires_at.asc())
        )
        .scalars()
        .all()
    )
    active = []
    archived = []
    for wl in rows:
        entry = {
            "id": wl.id,
            "title": wl.title,
            "template": wl.template,
            "private": wl.private,
            "expires_at": wl.expires_at.strftime("%Y-%m-%d"),
        }
        if wl.archived_at is None:
            active.append(entry)
        else:
            entry["archived_at"] = wl.archived_at.strftime("%Y-%m-%d")
            archived.append(entry)
    return jsonify({"active": active, "archived": archived})


@api_bp.post(
    "/lists"
)  # TODO: Flytt logikken for oppretting av liste hit fra controllers.py
@api_login_required  # TODO: Flytt validering av input til forms.py og kall form.validate() her
def create_list():
    """Opprett en ny ønskeliste for nåværende bruker."""
    json_data = request.get_json() or {}
    title = (json_data.get("title") or "").strip()
    template = json_data.get("template", "custom")
    custom_date_str: str | None = json_data.get("expires_at")

    custom_date = None
    if template == "custom":
        if not custom_date_str:
            return jsonify({"error": "Velg en utløpsdato."}), 400
        try:
            custom_date = datetime.strptime(custom_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            return jsonify({"error": "Ugyldig datoformat, forventet YYYY-MM-DD."}), 400

    try:
        expires_at = calculate_expires_at(
            template=template,
            user=current_user,
            custom_date=custom_date,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    now = datetime.now(timezone.utc)
    if expires_at <= now:
        return jsonify({"error": "Utløpsdatoen må være i fremtiden."}), 400

    if template in ("christmas", "birthday"):
        target_year = expires_at.year
        existing = (
            db.session.execute(
                db.select(WishList).where(
                    WishList.user_id == current_user.id,
                    WishList.template == template,
                    WishList.archived_at.is_(None),
                )
            )
            .scalars()
            .all()
        )
        duplicate = next(
            (wl for wl in existing if wl.expires_at.year == target_year), None
        )
        if duplicate:
            template_name = "jule" if template == "christmas" else "bursdags"
            return (
                jsonify(
                    {
                        "error": f"Du har allerede en {template_name}liste for {target_year}."
                    }
                ),
                409,
            )

    if template == "christmas":
        title = f"Jul {expires_at.year}"
    elif template == "birthday":
        title = f"Bursdag {expires_at.year}"
    elif not title:
        return jsonify({"error": "Listen må ha en tittel."}), 400

    if template == "custom":
        existing = db.session.execute(
            db.select(WishList).where(
                WishList.user_id == current_user.id,
                WishList.title == title,
                WishList.archived_at.is_(None),
            )
        ).scalar_one_or_none()
        if existing:
            return jsonify({"error": "Du har allerede en liste med samme tittel."}), 409

    new_list = WishList(
        user_id=current_user.id,
        title=title,
        template=template,
        expires_at=expires_at,
        private=bool(json_data.get("private", False)),
    )
    db.session.add(new_list)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logging.exception("Error creating wish list.")
        return jsonify({"error": "Det oppstod en feil ved oppretting av listen."}), 500

    return jsonify(
        {
            "id": new_list.id,
            "title": new_list.title,
            "expires_at": new_list.expires_at.strftime("%Y-%m-%d"),
        }
    ), 201


@api_bp.get("/lists/<int:list_id>/wishes")
@api_login_required
def get_archived_list_wishes(list_id: int):
    """Return wishes for an archived list owned by the current user.

    Security: claims are excluded at the query level (no selectinload) AND at
    the serializer level (dedicated function with no claim fields).  This
    ensures claimed_by is never exposed to the list owner regardless of how
    this endpoint is called.
    """
    wish_list = db.session.get(WishList, list_id)
    if wish_list is None:
        abort(404)
    if wish_list.user_id != current_user.id:
        abort(403)
    if wish_list.archived_at is None:
        return jsonify({"error": "Denne listen er ikke arkivert."}), 400

    wishes = (
        db.session.execute(
            db.select(Wish)
            # Intentionally NO selectinload(Wish.claims) — structural exclusion
            .where(Wish.list_id == list_id, Wish.deleted_at.is_(None))
            .order_by(Wish.desired.desc(), Wish.date_created.desc())
        )
        .scalars()
        .all()
    )
    return jsonify([_archived_wish_to_json(w) for w in wishes])


def _archived_wish_to_json(wish: Wish) -> dict:
    """Serialise a wish for display on an archived list.

    This function deliberately has NO access to claim data.  Do not add
    claim-related fields here.  For gifter-facing serialisation (where the
    viewer is NOT the wish owner) use wishes_to_json() instead.
    """
    return {
        "id": wish.id,
        "title": wish.title,
        "description": wish.description,
        "img_url": wish.img_url,
        "url": wish.url,
        "base_url": "{0.netloc}".format(urlsplit(wish.url)) if wish.url else "",
        "price": f"{wish.price:,}".replace(",", " ") if wish.price else "",
        "desired": wish.desired,
        "age": wish.time_since_creation(),
    }


@api_bp.post("/wishes/<int:wish_id>/generate-image")
@api_login_required
def generate_wish_image(wish_id: int) -> Response:
    import threading

    if not current_user.is_admin:
        abort(403)
    wish = db.session.get(Wish, wish_id)
    if wish is None or wish.deleted_at is not None:
        abort(404)
    json_data = request.get_json() or {}
    product_name: str = json_data.get("product_name") or wish.title
    description: str = wish.description or ""

    from flask import current_app

    from app.wishlist.image_generation import generate_image

    app = current_app._get_current_object()

    def _run() -> None:
        with app.app_context():
            try:
                file_path = generate_image(
                    product_name=product_name,
                    description=description,
                )
                filename = os.path.basename(file_path)
                _wish = db.session.get(Wish, wish_id)
                if _wish is not None:
                    _wish.img_url = f"/static/img/generated_images/{filename}"
                    _wish.img_broken_since = None
                    db.session.commit()
            except Exception:
                logging.exception(
                    "Background image generation failed for wish id=%d.", wish_id
                )

    threading.Thread(target=_run, daemon=True).start()
    return Response(status=202)


@api_bp.get("/wishes/<int:wish_id>/img-url")
@api_login_required
def get_wish_img_url(wish_id: int) -> Response:
    wish = db.session.get(Wish, wish_id)
    if wish is None or wish.deleted_at is not None:
        abort(404)
    return jsonify({"img_url": wish.img_url})


@api_bp.post("/wishes/<int:wish_id>/report-broken-image")
@api_login_required
def report_broken_image(wish_id: int) -> Response:
    wish = db.session.get(Wish, wish_id)
    if wish is None or wish.deleted_at is not None:
        abort(404)
    if wish.img_broken_since is None:
        wish.img_broken_since = datetime.now(timezone.utc)
        db.session.commit()
    return Response(status=204)


@api_bp.post("/wishes/<int:wish_id>/move")
@api_login_required
def move_wish(wish_id: int):
    """Move or copy a wish from an archived list to an active destination list.

    Payload:
      action              "move" | "copy"
      destination_list_id int | null   (use an existing active list)
      new_list            object | null {title, template, expires_at?}
                          (create a new list on the fly as the destination)

    "move": re-parents the wish (list_id updated); existing ClaimedWish rows
            follow automatically because they reference wish_id.
    "copy": creates a fresh Wish with no claims; original stays archived.
    """

    json_data = request.get_json() or {}
    action: str = json_data.get("action", "")
    destination_list_id: int | None = json_data.get("destination_list_id")
    new_list_data: dict | None = json_data.get("new_list")

    if action not in ("move", "copy"):
        return jsonify({"error": "Ugyldig handling. Bruk 'move' eller 'copy'."}), 400

    wish = db.session.get(Wish, wish_id)
    if wish is None or wish.deleted_at is not None:
        abort(404)
    if wish.user_id != current_user.id:
        abort(403)
    if wish.list_id is None:
        return jsonify({"error": "Ønsket tilhører ingen liste."}), 400

    source_list = db.session.get(WishList, wish.list_id)
    if source_list is None or source_list.archived_at is None:
        return jsonify({"error": "Ønsket er ikke på en arkivert liste."}), 400

    # Resolve destination list
    dest_list: WishList | None = None

    if new_list_data is not None:
        # Create a new list as the destination
        new_title = (new_list_data.get("title") or "").strip()
        new_template = new_list_data.get("template", "custom")
        new_expires_str: str | None = new_list_data.get("expires_at")

        if not new_title:
            return jsonify({"error": "Listetittel er påkrevd."}), 400
        if new_template not in ("christmas", "birthday", "custom"):
            return jsonify({"error": "Ugyldig mal."}), 400

        custom_date: datetime | None = None
        if new_template == "custom":
            if not new_expires_str:
                return jsonify({"error": "Velg en utløpsdato."}), 400
            try:
                custom_date = datetime.strptime(new_expires_str, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                return jsonify({"error": "Ugyldig datoformat."}), 400

        try:
            new_expires_at = calculate_expires_at(
                template=new_template,
                user=current_user,
                custom_date=custom_date,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        dest_list = WishList(
            user_id=current_user.id,
            title=new_title,
            template=new_template,
            expires_at=new_expires_at,
        )
        db.session.add(dest_list)
        db.session.flush()

    elif destination_list_id is not None:
        dest_list = db.session.get(WishList, destination_list_id)
        if dest_list is None:
            abort(404)
        if dest_list.user_id != current_user.id:
            abort(403)
        if dest_list.archived_at is not None:
            return jsonify({"error": "Kan ikke flytte til en arkivert liste."}), 400
    else:
        return jsonify({"error": "Angi destination_list_id eller new_list."}), 400

    if action == "move":
        wish.list_id = dest_list.id
    else:
        # Copy: fresh wish, no claims
        new_wish = Wish(
            user_id=current_user.id,
            list_id=dest_list.id,
            title=wish.title,
            description=wish.description,
            url=wish.url,
            img_url=wish.img_url,
            price=wish.price,
            desired=wish.desired,
            quantity=wish.quantity,
        )
        db.session.add(new_wish)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logging.exception("Error moving/copying wish %d.", wish_id)
        return jsonify({"error": "Det oppstod en feil. Prøv igjen."}), 500

    return jsonify({"success": True, "destination_list_id": dest_list.id}), 200


@api_bp.post("/wish-list/update")
@api_login_required
def update_wish_list():
    return "ok", 200
