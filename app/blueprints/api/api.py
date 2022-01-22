from urllib.parse import urlsplit
from flask import Blueprint, render_template, request, jsonify, redirect
from flask_login import current_user
from app.models import User, Wish, CoWishUser
from app.forms import SearchForm, WishForm, ClaimForm, GetWishesForm
from app import db

api_bp = Blueprint("api", __name__,
                   template_folder='templates',
                   static_folder='static', static_url_path='')

default_image = "https://static.vecteezy.com/system/resources/previews/000/384/023/original/"\
    "sketch-of-a-wrapped-gift-box-vector.jpg"


@api_bp.route("/search", methods=["GET", "POST"])
def search():
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
        return render_template("search.html", searchform=searchform)


@api_bp.route("/add", methods=["POST"])
def add():
    form = WishForm()
    if form.validate():
        if not form.wish_img_url.data:
            form.wish_img_url.data = default_image
        new_wish = Wish(user_id=current_user.id, wish_title=form.wish_title.data,
                        description=form.wish_description.data, url=form.wish_url.data, img_url=form.wish_img_url.data,
                        desired=form.desired.data)
        if new_wish:
            try:
                db.session.add(new_wish)
                db.session.commit()
                print("Wish ID: " + str(new_wish.id))
            except:
                return "Det oppstod en feil ved oppretting av ønsket"

            add_co_wisher(form.co_wisher.data, form.id.data)

            return redirect(request.referrer)
        else:
            return "Noe gikk galt, fikk ikke lagt til ønske."
    else:
        return "Noe gikk galt, fikk ikke lagt til ønske."


@api_bp.route("/update", methods=["POST"])
def update():
    wishform = WishForm()
    if wishform.validate():
        if wishform.edit_id.data:
            wish = Wish.query.get(wishform.edit_id.data)
            if wish.user_id == current_user.id:
                wish.wish_title = wishform.wish_title.data
                wish.description = wishform.wish_description.data
                wish.url = wishform.wish_url.data
                wish.img_url = wishform.wish_img_url.data
                wish.desired = 1 if wishform.desired.data else 0
                add_co_wisher(wishform.co_wisher.data, wish.id)
                print()
                try:
                    db.session.commit()
                except:
                    pass

                return render_template("wish_modal_edit_content.html", wish=wish, wishform=wishform)

    return "Det oppstod en feil ved oppdatering av ønske"


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
        wish = Wish.query.get(claim.claimed_wish_id.data)
        if not wish.claimed_by_user_id and wish.user_id != current_user.id:  # Sjekker ikke om bruker har lov til å ta valgte ønske
            wish.claimed_by_user_id = current_user.id

        elif wish.claimed_by_user_id == current_user.id:
            wish.claimed_by_user_id = 0

        else:
            return "Feil ved claiming"

        try:
            db.session.commit()

        except:
            return "Det oppstod en feil med å ta ønsket."

        # return redirect(url_for(file))


@api_bp.route("/wish", methods=["POST"])
def wish():
    return 0


@api_bp.route("/cowisher", methods=["POST"])
def cowisher():
    user_id = User.query.get(request.values.get("user_id"))
    if user_id:
        return jsonify(success=True)
    else:
        return "Record not found", 400


def add_co_wisher(co_wisher, wish_id):
    if co_wisher:
        for user in co_wisher:
            new_co_wisher = CoWishUser(id=wish_id, co_wish_user_id=user)
            try:
                db.session.add(new_co_wisher)
            except:
                return "Det oppstod en feil ved oppretting av ønsket"


def wishes_json(filter, num_of_col=4):
    try:
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

        while (filtered_wishes):
            for i in range(num_of_col):
                if not filtered_wishes: break
                column_order[i].append(filtered_wishes.pop(0))

        wishes_arranged = []
        for i in range(num_of_col):
            jsonstring = [e.tojson() for e in column_order[i]]
            wishes_arranged.append(jsonstring)

        json_output = jsonify(wishes_arranged)

        return json_output
    except:
        return "Kunne ikke hente ønsker"
