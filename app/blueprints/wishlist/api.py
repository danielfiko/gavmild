from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.blueprints.auth.models import User
from sqlalchemy import func
from app.forms import WishForm, AjaxForm
from app.database.database import db
from app.blueprints.wishlist.models import Wish, CoWishUser, ClaimedWish
from sqlalchemy import or_, and_, exc, asc, desc
from urllib.parse import urlsplit


api_bp = Blueprint('api', __name__, template_folder="templates/wishlist", url_prefix='/api') # static_folder='static/views'


# TODO: Finn et bedre navn på ruta
# TODO: Ikke returner valgte navn
# TODO: Verifiser at det ikke er duplikater
@api_bp.route("/typeahead", methods=["GET", "POST"])
def typeahead():
    searchform = AjaxForm()
    if request.method == "POST":
        if searchform.validate():
            searchbox = searchform.searchbox.data
            result = User.query.filter(User.username.like(searchbox + "%")).limit(5).all()
            jsonstring = jsonify([e.tojson() for e in result])
            return jsonstring
        elif request.form["hello"]:
            print("hello")
            result = User.query.filter(User.username.like("%")).all()
            jsonstring = jsonify([e.tojson() for e in result])
            return jsonstring
    else:
        return "MeRkElIgE gReIeR", 500


@api_bp.route("/add", methods=["POST"])
def add():
    form = WishForm()
    if form.validate():
        if len(form.wish_img_url.data) < 5:
            form.wish_img_url.data = url_for('static', filename='gift-default.png')
        try:
            new_wish = Wish(user_id=current_user.id, title=form.wish_title.data,
                        description=form.wish_description.data, quantity=form.quantity.data, url=form.wish_url.data,
                        img_url=form.wish_img_url.data, desired=form.desired.data, price=form.price.data)
        except:
            return "Wish model creation failed", 400
        if new_wish:
            try:
                flash("Ønsket ble lagt til")
                db.session.add(new_wish)
                db.session.commit()
            except:
                flash("Det oppstod en feil, gi Daniel beskjed")
                return "Det oppstod en feil ved oppretting av ønsket", 500

            # FIXME: Kun ta i mot liste (tar i mot string nå og lagrer komma i tabellen)
            if form.co_wisher.data:
                for user_id in form.co_wisher.data:
                    new_co_wisher = CoWishUser(id=new_wish.id, co_wish_user_id=user_id)
                    db.session.add(new_co_wisher)
                db.session.commit()

            return jsonify({'success': True}), 200, {'ContentType': 'application/json'}
    print(form.errors)
    return "Form did not validate", 400


# TODO: Ikke ta i mot GET, håndter alt i ajax så bruker ikke ser denne ruta
@api_bp.route("/update", methods=["POST"])
def update():
    wishform = WishForm()
    if wishform.validate() and wishform.edit_id.data:
        wish = Wish.query.get(wishform.edit_id.data)
        if wish.user_id == current_user.id:
            wish.title = wishform.wish_title.data
            wish.description = wishform.wish_description.data
            wish.quantity = wishform.quantity.data
            wish.url = wishform.wish_url.data
            wish.price = wishform.price.data
            if len(wish.img_url) < 5:
                wish.img_url = url_for('static', filename='gift-default.png')
            else:
                wish.img_url = wishform.wish_img_url.data
            wish.desired = 1 if wishform.desired.data else 0
            form_co_wishers = wishform.co_wisher.data.split(",")
            if form_co_wishers[0]:
                for user_id in form_co_wishers:
                    new_co_wisher = CoWishUser(id=wishform.edit_id.data, co_wish_user_id=user_id)
                    if new_co_wisher:
                        db.session.add(new_co_wisher)
            try:
                db.session.commit()
            except Exception as error:
                print(str(error.orig) + " for parameters" + str(error.params))

            return redirect(request.referrer)
    return "Noe gikk galt med oppdatering av ønske", 400


@api_bp.route("/delete", methods=["POST"])
def delete():
    wish = Wish.query.get(request.values.get("id"))
    if wish.user_id == current_user.id:
        try:
            db.session.delete(wish)
            db.session.commit()
            return "Ønske slettet"
        except:
            return "Noe gikk galt - kunne ikke slette ønsket", 400
    else:
        return "Noe gikk galt", 400


@api_bp.route("/claim", methods=["POST"])
def claim():
    form = AjaxForm()
    if form.validate():
        wish = Wish.query.get(form.claimed_wish_id.data)
        if not wish.claims and wish.user_id != current_user.id:# Sjekker ikke om bruker har lov til å ta valgte ønske
            claim = ClaimedWish(wish_id=form.claimed_wish_id.data, user_id=current_user.id, quantity=1)
            db.session.add(claim)
            db.session.commit()
        elif wish.is_claimed_by_user(current_user.id):
            ClaimedWish.query.filter(ClaimedWish.user_id == current_user.id, ClaimedWish.wish_id == wish.id).delete()

        else:
            return "Feil ved claiming", 400

        try:
            db.session.commit()

        except:
            return "Det oppstod en feil med å ta ønsket.", 500

        return redirect(request.referrer)


@api_bp.route("/wish/all", methods=["POST"])
def wish_mobile():
    wishes = Wish.query.filter(Wish.user_id != current_user.id) \
        .order_by(desc(Wish.date_created), desc(Wish.desired)).limit(30).all()

    return wishes_to_json(wishes)


@api_bp.route("/wish/claimed", methods=["POST"])
def claimed():
    form = AjaxForm()
    if form.validate():
        wishes = Wish.query.filter(Wish.claims.any(ClaimedWish.user_id == current_user.id)).all()
    return wishes_to_json(wishes)


# TODO: Legg til mulighet for å fjerne seg selv som co wisher
# TODO: Ha separat "ønsker meg mest" for co wishere
# TODO: Bestem redigeringsrettigheter/sletterettigheter for co wisher
@api_bp.route("/wish/user/<int:user_id>", methods=["POST"])
def return_user_wishes(user_id):
    form = AjaxForm()
    if form.validate():
        wishes = Wish.query.filter(or_(Wish.user_id == user_id, Wish.co_wishers
                                        .any(CoWishUser.co_wish_user_id == user_id))) \
                                        .order_by(Wish.desired.desc(), Wish.date_created.desc()).all()
        return wishes_to_json(wishes)


@api_bp.route("/wish/new", methods=["POST"])
def new_wish():
    wish_form = WishForm()
    claim_form = AjaxForm()
    empty_wish = Wish(user_id="", title="", description="", url="",
                      img_url=url_for('static', filename='gift-default.png'), desired="")
    return render_template("wish_modal_edit_content.html", wish=empty_wish, wish_form=wish_form, claimform=claim_form,
                           form_action="add")


@api_bp.route("/wish", methods=["POST"])
def return_modal():
    form = AjaxForm()
    claim_form = AjaxForm()
    if form.validate():
        wish = Wish.query.filter(Wish.id == form.wish_id.data).first()

        for claim in wish.claims:
            print(claim.user.first_name)

        # Returnere redigerbart ønske
        if wish.user_id == current_user.id:
            wish_form = WishForm()
            return render_template("wish_modal_edit_content.html", wish=wish,
                                   claimform=claim_form, wish_form=wish_form, form_action="update")
        # Returnere andres ønske
        else:
            netloc = "{0.netloc}".format(urlsplit(wish.url))
            return render_template("wish_modal_view_content.html", wish=wish, claimform=claim_form, netloc=netloc)
    else:
        return "getwishesform didn't validate"


# FIXME: Tullete å kalle denne for hver bruker som blir lagt i lista
@api_bp.route("/cowisher", methods=["POST"])
def cowisher():
    user_id = User.query.get(request.values.get("user_id"))
    if user_id:
        return jsonify(success=True)
    else:
        return "Record not found", 400


def wishes_to_json(wishes):
    wishes_json_string = []
    co_wishers = []
    for whs in wishes:
        wishes_json_string.append({
            "id": whs.id,
            "claimed": True if whs.claims and whs.user_id != current_user.id else False,
            "img_url": whs.img_url,
            "first_name": whs.user.first_name,
            "co_wisher": whs.get_co_wishers(),
            "age": whs.time_since_creation(),
            "title": whs.title,
            "price": f"{whs.price:,}".replace(",", " ") if whs.price else "",
            "desired": whs.desired,
            "base_url": "{0.netloc}".format(urlsplit(whs.url))
        })
    if wishes_json_string:
        return jsonify(wishes_json_string)
    else:
        return jsonify({}), 200, {'ContentType': 'application/json'}