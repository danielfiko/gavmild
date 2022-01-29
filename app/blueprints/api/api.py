from datetime import datetime
from urllib.parse import urlsplit
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import current_user
from sqlalchemy import or_

from app.models import User, Wish, CoWishUser
from app.forms import SearchForm, WishForm, ClaimForm, GetWishesForm
from app import db

api_bp = Blueprint("api", __name__,
                   template_folder='templates',
                   static_folder='static', url_prefix="/api")


# TODO: Finn et bedre navn på ruta
# TODO: Ikke returner valgte navn
# TODO: Verifiser at det ikke er duplikater
@api_bp.route("/typeahead", methods=["GET", "POST"])
def typeahead():
    searchform = SearchForm()
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
            form.wish_img_url.data = url_for('views.static', filename='gift-default.png')
        new_wish = Wish(user_id=current_user.id, title=form.wish_title.data,
                        description=form.wish_description.data, url=form.wish_url.data, img_url=form.wish_img_url.data,
                        desired=form.desired.data)
        if new_wish:
            try:
                db.session.add(new_wish)
                db.session.commit()
                print("Wish ID: " + str(new_wish.id))
            except:
                return "Det oppstod en feil ved oppretting av ønsket"

            add_co_wisher(form.co_wisher.data, new_wish.id)

            return render_template("list_item.html", wish=new_wish, user=new_wish.user_name(),
                                   co_wisher=new_wish.co_wisher())

    return "Noe gikk galt, fikk ikke lagt til ønske."


# TODO: Ikke ta i mot GET, håndter alt i ajax så bruker ikke ser denne ruta
@api_bp.route("/update", methods=["POST"])
def update():
    wishform = WishForm()
    if wishform.validate():
        if wishform.edit_id.data:
            wish = Wish.query.get(wishform.edit_id.data)
            if wish.user_id == current_user.id:
                wish.title = wishform.wish_title.data
                wish.description = wishform.wish_description.data
                wish.url = wishform.wish_url.data
                wish.img_url = wishform.wish_img_url.data
                wish.desired = 1 if wishform.desired.data else 0
                form_co_wishers = wishform.co_wisher.data.split(",")
                co_wishers = []
                for w in form_co_wishers:
                    co_wishers.append(int(w))
                add_co_wisher(co_wishers, wish.id)
                if len(wish.img_url) < 5:
                    wish.img_url = url_for('views.static', filename='gift-default.png')
                try:
                    db.session.commit()
                except:
                    return "update failed"

                return redirect(request.referrer)
    return "Noe gikk galt med oppdatering av ønske"


@api_bp.route("/delete", methods=["POST"])
def delete():
    wish = Wish.query.get(request.values.get("id"))
    if wish.user_id == current_user.id:
        try:
            db.session.delete(wish)
            db.session.commit()
            return "Ønske slettet"
        except:
            return "Noe gikk galt - kunne ikke slette ønsket"
    else:
        return "Noe gikk galt"


@api_bp.route("/claim", methods=["POST"])
def claim():
    form = ClaimForm()
    if form.validate():
        wish = Wish.query.get(form.claimed_wish_id.data)
        if not wish.claimed_by_user_id and wish.user_id != current_user.id:  # Sjekker ikke om bruker har lov til å ta valgte ønske
            wish.claimed_by_user_id = current_user.id
            wish.date_claimed = datetime.utcnow()

        elif wish.claimed_by_user_id == current_user.id:
            wish.claimed_by_user_id = 0

        else:
            return "Feil ved claiming"

        try:
            db.session.commit()

        except:
            return "Det oppstod en feil med å ta ønsket."

        return redirect(request.referrer)


@api_bp.route("/wish/all", methods=["POST"])
def wish_mobile():
    wishes = db.session.query(Wish, User).select_from(Wish).join(CoWishUser, isouter=True) \
        .join(User, User.id == Wish.user_id) \
        .order_by(Wish.date_created, Wish.desired.desc()).limit(30).all()

    return wishes_to_json(wishes)


def new_all_wishes():
    form = GetWishesForm()
    if form.validate():
        wishes = db.session.query(Wish, User).select_from(Wish).join(CoWishUser, isouter=True) \
            .join(User, User.id == Wish.user_id).filter(User.id != current_user.id) \
            .order_by(Wish.date_created, Wish.desired.desc()).limit(30).all()

    wishes = populate_colums(wishes, form.columns.data)
    return render_template("list_wishes.html", wishes=wishes)


@api_bp.route("/wish/claimed", methods=["POST"])
def claimed():
    form = GetWishesForm()
    if form.validate():
        wishes = db.session.query(Wish, User).join(User, User.id == Wish.user_id) \
            .filter(Wish.claimed_by_user_id == current_user.id) \
            .order_by(Wish.date_claimed.desc()).all()
    wishes = populate_colums(wishes, form.columns.data)
    return render_template("list_wishes.html", wishes=wishes)


# TODO: Legg til mulighet for å fjerne seg selv som co wisher
# TODO: Ha separat "ønsker meg mest" for co wishere
# TODO: Bestem redigeringsrettigheter/sletterettigheter for co wisher
@api_bp.route("/wish/user/<int:user_id>", methods=["POST"])
def user_wishes(user_id):
    form = GetWishesForm()
    if form.validate():
        wishes = db.session.query(Wish, User).select_from(Wish).join(CoWishUser, isouter=True) \
            .join(User, User.id == Wish.user_id)\
            .filter(or_(Wish.user_id == user_id, CoWishUser.co_wish_user_id == user_id)) \
            .order_by(Wish.desired.desc(), Wish.date_created.desc()).all()
        return wishes_to_json(wishes)


def all_wishes():
    form = GetWishesForm()
    if form.validate():
        return wishes_json(form.filter.data)


@api_bp.route("/wish/new", methods=["POST"])
def new_wish():
    wish_form = WishForm()
    claim_form = ClaimForm()
    empty_wish = Wish(user_id="", title="", description="", url="",
                      img_url=url_for('views.static', filename='gift-default.png'), desired="")
    return render_template("wish_modal_edit_content.html", wish=empty_wish, wish_form=wish_form, claimform=claim_form,
                           form_action="add")


@api_bp.route("/wish", methods=["POST"])
def wish():
    form = GetWishesForm()
    claim_form = ClaimForm()
    if form.validate():
        cur_wish = db.session.query(Wish, User).join(User, User.id == Wish.user_id)\
            .filter(Wish.id == form.wish_id.data).first()
        co_wisher = cur_wish[0].co_wisher()

        # Returnere redigerbart ønske
        if cur_wish[0].user_id == current_user.id:
            wish_form = WishForm()
            return render_template("wish_modal_edit_content.html", wish=cur_wish[0], user=cur_wish[1],
                                   co_wisher=co_wisher, claimform=claim_form, wish_form=wish_form, form_action="update")
        # Returnere andres ønske
        else:
            netloc = "{0.netloc}".format(urlsplit(cur_wish[0].url))
            return render_template("wish_modal_view_content.html", wish=cur_wish[0], user=cur_wish[1],
                                   claimform=claim_form, netloc=netloc, co_wisher=co_wisher)
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


# FIXME: Kun ta i mot liste (tar i mot string nå og lagrer komma i tabellen)
def add_co_wisher(co_wisher, wish_id):
    if co_wisher:
        for user in co_wisher:
            new_co_wisher = CoWishUser(id=wish_id, co_wish_user_id=user)
            db.session.add(new_co_wisher)
        try:
            db.session.commit()
        except:
            return "Det oppstod en feil ved oppretting av ønsket"


def wishes_to_json(wishes):
    wishes_json_string = []
    co_wishers = []
    for w, u in wishes:
        for co_wisher in w.co_wisher():
            co_wishers.append(co_wisher.fist_name)
        wishes_json_string.append({
            "id": w.id,
            "claimed": True if w.claimed_by_user_id and w.user_id != current_user.id else False,
            "img_url": w.img_url,
            "first_name": u.first_name,
            "co_wisher": co_wishers,
            "age": w.time_since_creation(),
            "title": ("<span>&#9733; </span>" if w.desired else "") + w.title
        })
    return jsonify(wishes_json_string)


def populate_colums(wishes, columns):
    current_column = 0
    wishes_by_column = [[] for x in range(columns)]
    if columns > 4:
        return "Joe mama"
    for w in wishes:
        wishes_by_column[current_column].append(w)
        if current_column < columns - 1:
            current_column += 1
        else:
            current_column = 0
    return wishes_by_column


def wishes_json(filter, num_of_col=4):
    # try:
    desired = []
    wish = []
    wishes = Wish.query.order_by(Wish.date_created).all()

    def filter_and_append(w):
        if w.desired:
            desired.append(w)
        else:
            wish.append(w)

    for w in wishes:
        if filter == "own" and w.user_id == current_user.id:
            filter_and_append(w)
        if filter == "claimed" and w.claimed_by_user_id == current_user.id:
            filter_and_append(w)
        if filter == "all_but_own" and w.user_id != current_user.id:
            filter_and_append(w)

    filtered_wishes = desired + wish

    column_order = []
    for i in range(num_of_col):
        if not filtered_wishes: break
        column_order.append([filtered_wishes.pop(0)])

    while filtered_wishes:
        for i in range(num_of_col):
            if not filtered_wishes: break
            column_order[i].append(filtered_wishes.pop(0))

    wishes_arranged = []
    for i in range(num_of_col):
        jsonstring = [e.tojson() for e in column_order[i]]
        wishes_arranged.append(jsonstring)
        if i >= len(column_order) - 1:
            break

    json_output = jsonify(wishes_arranged)

    return json_output
# except:
# return "Kunne ikke hente ønsker"
