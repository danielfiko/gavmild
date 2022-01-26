from urllib.parse import urlsplit

from flask import Blueprint, render_template
from flask_login import current_user

from app import db
from app.forms import ClaimForm
from app.models import Wish, User, CoWishUser

wishes_bp = Blueprint("wishes", __name__,
                      template_folder='templates',
                      static_folder='static', static_url_path='')




'''
    # Spør etter eget ønske
    if self.wish[0].user_id == current_user.id:
        delete = '<a id="' + str(self.wish[0].id) + '"class="delete-wish">Slett</a>'
        wish_values = [self.wish[0].wish_title, self.wish[0].description, self.wish[0].url, self.wish[0].img_url]
        for value in wish_values:
            if value:
                # Kan ikke appende til co_wisher
                form_values.append(value)
            else:
                form_values.append(wishform.wish_description.render_kw["placeholder"])
        form_values.append(co_wisher)
        form_values.append(self.wish[0].id)
        return render_template("wish_modal_edit_content.html", wish=self.wish[0], wishform=wishform, delete=delete,
                               form_values=form_values, form_action="update")


    # Oppetter nytt ønske
    elif form.new_wish.data:
        form_values = [0] * 4
        form_values.append([0])
        wish = Wish(img_url=default_image)
        return render_template("wish_modal_edit_content.html", wish=wish, wishform=wishform,
                               form_values=form_values, form_action="add")

    # Henter alle ønsker
    else:
        filter = form.filter.data
        return wishes_json(filter)


def wish_data_edit(wish_id):
    form_values = []
    co_wisher = [0]

    wish = db.session.query(Wish, User.username).join(User, User.id == Wish.user_id).filter(
        Wish.id == wish_id).one()
    query = db.session.query(User.username, User.id).join(CoWishUser).filter(
        CoWishUser.id == form.id.data).all()
    if query:
        if len(query) > 1:
            co_wisher = [[[" ," + e.email.capitalize(), e.id]] for e in query]
            co_wisher[-1] = " og " + str(query[-1].email.capitalize())
        else:
            co_wisher = [[query[0].email.capitalize(), query[0].id]]
        print(co_wisher)
    # Spør etter eget ønske
    if self.wish[0].user_id == current_user.id:
        delete = '<a id="' + str(self.wish[0].id) + '"class="delete-wish">Slett</a>'
        wish_values = [self.wish[0].wish_title, self.wish[0].description, self.wish[0].url, self.wish[0].img_url]
        for value in wish_values:
            if value:
                # Kan ikke appende til co_wisher
                form_values.append(value)
            else:
                form_values.append(wishform.wish_description.render_kw["placeholder"])
        form_values.append(co_wisher)
        form_values.append(self.wish[0].id)
        return render_template("wish_modal_edit_content.html", wish=self.wish[0], wishform=wishform, delete=delete,
                               form_values=form_values, form_action="update")

    # Spør etter andres ønske
    else:
        claimform = ClaimForm()
        netloc = "{0.netloc}".format(urlsplit(self.wish[0].url))
        co_wisher.insert(0, self.wish[1])
        return render_template("wish_modal_view_content.html", wish=self.wish[0], claimform=claimform, netloc=netloc,
                               co_wisher=co_wisher, form_values=form_values, form_action="")

    # Oppetter nytt ønske
    if form.new_wish.data:
        form_values = [0] * 4
        form_values.append([0])
        wish = Wish(img_url=default_image)
        return render_template("wish_modal_edit_content.html", wish=wish, wishform=wishform,
                               form_values=form_values, form_action="add")

    # Henter alle ønsker
    else:
        filter = form.filter.data
        return wishes_json(filter)'''