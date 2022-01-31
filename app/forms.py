from flask_wtf import FlaskForm
from markupsafe import Markup
from wtforms import StringField, PasswordField, EmailField, DateField, SubmitField, TextAreaField, BooleanField, \
    HiddenField, SelectField, IntegerField, URLField
from wtforms.validators import InputRequired, Length, ValidationError, Email, NumberRange

from .models import User


def validate_username(username):
    existing_user_username = User.query.filter_by(username=username.data).first()

    if existing_user_username:
        raise ValidationError("Brukernavet finnes fra før. Velg et annet brukernavn")


class RegisterForm(FlaskForm):
    first_name = StringField("Fornavn", validators=[InputRequired(), Length(min=1, max=50)])
    last_name = StringField("Etternavn", validators=[Length(max=50)])
    email = EmailField("E-post", validators=[InputRequired(), Email()], render_kw={"placeholder": "E-post"})
    password = PasswordField("Passord", validators=[InputRequired(), Length(min=8, max=90)],
                             render_kw={"placeholder": "Passord"})
    date_of_birth = DateField("Fødselsdato", validators=[InputRequired()])
    submit = SubmitField("Opprett konto")


class LoginForm(FlaskForm):
    email = EmailField("E-post", validators=[InputRequired(), Email()], render_kw={"placeholder": "E-post"})
    password = PasswordField("Passord", validators=[InputRequired(), Length(min=4, max=90)],
                             render_kw={"placeholder": "Passord"})
    new_password = PasswordField("Nytt passord", validators=[Length(min=0, max=90)],
                                 render_kw={"placeholder": "Nytt passord"})
    submit = SubmitField("Logg inn")


class WishForm(FlaskForm):
    wish_title = StringField("Ønske", validators=[InputRequired(), Length(min=2, max=90)], id="title",
                             render_kw={"placeholder": "Hva ønsker du deg?", "form": "wishform"})
    wish_description = \
        TextAreaField("Detaljer", validators=[Length(min=0, max=255)],
                      render_kw={"placeholder": "Farge, størrelse o.l.", "form": "wishform"},
                      id="description")
    wish_url = StringField("Lenke", validators=[Length(min=0, max=255)],
                        render_kw={"placeholder": "Lenke til nettside for produktet",
                                   "form": "wishform"}, id="url")
    wish_img_url = URLField("Legg til nytt bilde", validators=[Length(min=0, max=255)],
                            render_kw={"placeholder": "Lenke til bilde av produktet", "form": "wishform"},
                            id="img_url")
    desired = BooleanField(Markup(" Ønsker meg mest"), render_kw={"form": "wishform"})
    co_wisher = HiddenField("Ønsk sammen med", render_kw={"form": "wishform"})
    quantity = SelectField("Antall", render_kw={"form": "wishform"}, choices=[(i, i) for i in range(1, 11)])
    price = IntegerField("Pris", render_kw={"form": "wishform", "placeholder": "Pr. stk.", "min": 0},
                         validators=[NumberRange(max=1000000)])
    edit_id = HiddenField(render_kw={"form": "wishform"})
    submit = SubmitField("Lagre", render_kw={"form": "wishform"})


class AjaxForm(FlaskForm):
    # Claiming
    claimed_wish_id = StringField(render_kw={"type": "hidden"}, id="claimed_wish_id")
    unclaim_btn = SubmitField("Ikke ta", render_kw={"class": "button"})
    claim_btn = SubmitField("Ta", render_kw={"class": "button"})
    # Typeahead
    searchbox = StringField(id="livebox")
    # Filter for ønsker
    filter = StringField(render_kw={"type": "hidden"})
    # API for henting av ønsker
    wish_id = IntegerField()
    columns = IntegerField()
