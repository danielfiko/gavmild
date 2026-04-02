import datetime
import random
from flask_wtf import FlaskForm
from markupsafe import Markup
from wtforms import (
    StringField,
    PasswordField,
    EmailField,
    DateField,
    SubmitField,
    TextAreaField,
    BooleanField,
    HiddenField,
    SelectField,
    IntegerField,
    URLField,
    RadioField,
)
from wtforms.validators import (
    InputRequired,
    Length,
    ValidationError,
    Email,
    NumberRange,
    Optional,
)

from app import db
from app.auth.models import (
    User,
)  # TODO: Direct import of User model creates tight coupling between forms and models. Consider moving DB-dependent validation to the view layer.


def validate_username(username):
    existing_user = db.session.execute(
        db.select(User).where(User.username == username.data)
    ).scalar_one_or_none()

    if existing_user:
        raise ValidationError("Brukernavet finnes fra før. Velg et annet brukernavn")


class RegisterForm(FlaskForm):
    first_name = StringField(
        "Fornavn", validators=[InputRequired(), Length(min=1, max=50)]
    )
    last_name = StringField("Etternavn", validators=[Length(max=50)])
    email = EmailField(
        "E-post",
        validators=[InputRequired(), Email()],
        render_kw={"placeholder": "E-post"},
    )
    password = PasswordField(
        "Passord",
        validators=[InputRequired(), Length(min=8, max=90)],
        render_kw={"placeholder": "Passord"},
    )
    date_of_birth = DateField("Fødselsdato", validators=[InputRequired()])
    submit = SubmitField("Opprett konto")


class LoginForm(FlaskForm):
    email = EmailField(
        "E-post",
        validators=[InputRequired(), Email()],
        render_kw={"placeholder": "E-post"},
    )
    password = PasswordField(
        "Passord",
        validators=[InputRequired(), Length(min=8, max=90)],
        render_kw={"placeholder": "Passord"},
    )
    new_password = PasswordField(
        "Nytt passord",
        validators=[Length(min=0, max=90)],
        render_kw={"placeholder": "Nytt passord"},
    )
    remember_me = BooleanField("Husk meg", render_kw={"placeholder": "Husk meg"})
    submit = SubmitField("Logg inn")


class ChangePasswordForm(FlaskForm):
    new_password = PasswordField(
        "Nytt passord",
        validators=[Length(min=8, max=90)],
        render_kw={"placeholder": "Nytt passord"},
    )
    submit = SubmitField("Endre passord")


class WishForm(FlaskForm):
    wish_title = StringField(
        "Ønske",
        validators=[InputRequired(), Length(min=2, max=90)],
        id="title",
        render_kw={"placeholder": "Hva ønsker du deg?", "form": "wishform"},
    )
    wish_description = TextAreaField(
        "Detaljer",
        validators=[Length(min=0, max=255)],
        render_kw={"placeholder": "Farge, størrelse o.l.", "form": "wishform"},
        id="description",
    )
    wish_url = URLField(
        "Lenke",
        validators=[Length(min=0, max=255)],
        render_kw={
            "placeholder": "Lenke til nettside for produktet",
            "form": "wishform",
        },
        id="url",
    )
    wish_img_url = StringField(
        "Legg til nytt bilde",
        validators=[Length(min=0, max=255)],
        render_kw={"placeholder": "Lenke til bilde av produktet", "form": "wishform"},
        id="img_url",
    )
    desired = BooleanField(Markup(" Ønsker meg mest"), render_kw={"form": "wishform"})
    co_wisher = HiddenField("Ønsk sammen med", render_kw={"form": "wishform"})
    quantity = SelectField(
        "Antall", render_kw={"form": "wishform"}, choices=[(i, i) for i in range(1, 11)]
    )
    price = IntegerField(
        "Pris",
        render_kw={"form": "wishform", "placeholder": "Pr. stk.", "min": 0},
        validators=[NumberRange(max=1000000), Optional()],
    )
    list_id = SelectField(
        "Ønskeliste",
        coerce=int,
        validators=[Optional()],
        choices=[],
        render_kw={"form": "wishform"},
    )
    edit_id = HiddenField(render_kw={"form": "wishform"})
    submit = SubmitField("Lagre", render_kw={"form": "wishform"})


class ProductForm(FlaskForm):
    product = StringField(
        "Ønske",
        validators=[InputRequired(), Length(min=2, max=255)],
        render_kw={"placeholder": "Lim inn en lenke eller skriv hva du ønsker deg", "form": "productform"},
    )
    submit = SubmitField("Videre", render_kw={"form": "productform"}) 
    


class MyBaseForm(FlaskForm):
    class Meta:
        locales = ["nb"]

        def get_translations(self, form):
            return super(FlaskForm.Meta, self).get_translations(form)


class WishListForm(MyBaseForm):
    title = StringField(
        "Listenavn",
        validators=[
            InputRequired(),
            Length(min=2, max=90, message="Listenavn må være mellom 2 og 90 tegn."),
        ],
        id="title",
        render_kw={"form": "list_form"},
    )
    template = RadioField(
        "Mal",
        choices=[
            ("christmas", "Jul"),
            ("birthday", "Bursdag"),
            ("custom", "Egendefinert"),
        ],
        default="custom",
        render_kw={"form": "list_form"},
    )
    private = RadioField(
        "Privat liste?",
        choices=["Ja", "Nei"],
        default="Nei",
        render_kw={"form": "list_form"},
    )
    expires_at = DateField(
        "Utløpsdato", validators=[Optional()], render_kw={"form": "list_form"}
    )
    submit = SubmitField("Lagre", render_kw={"form": "list_form"})

    @staticmethod
    def get_title_placeholder():
        return random.choice(
            [
                "Min drømmeønskeliste: Alt jeg ønsker meg!",
                f"Fremtidige skatter: Min ønskeliste {datetime.date.today().year}",
                "Gavetips: Det jeg ønsker meg akkurat nå",
                "Ønsker og drømmer: Min ultimate ønskeliste",
                "Juleønsker: Ønsker meg til høytiden",
                "Bursdagsønsker: Gaver som vil glede meg",
                "Min elleville ønskeliste: Alt jeg drømmer om",
                "Gavetrangen: Ønsker meg disse skattene",
                "Skjem meg bort: Tingene jeg ønsker meg mest",
                "Favorittønsker: Det jeg virkelig drømmer om",
                "Luksusønskeliste: Gaver fra mine drømmer",
                "En verden av ønsker: Mitt ønskeliste-eventyr",
                "Hjemmeønsker: Skatter for mitt eget rike",
                "Gavetips til meg: Min personlige ønskeliste",
                "Skatter av mitt hjerte: Ønsker meg disse gavene",
            ]
        )


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


class TelegramConnectForm(FlaskForm):
    pass


class APIform(FlaskForm):
    pass  # TODO: Implementer


class CredentialForm(FlaskForm):
    entry_id = IntegerField(validators=[InputRequired()])
    label = StringField(validators=[Optional(), Length(min=2, max=90)])
    submit = SubmitField("Lagre")
