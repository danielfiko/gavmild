import json
import secrets
from datetime import datetime
from functools import wraps

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    RegistrationCredential,
    AuthenticationCredential, ResidentKeyRequirement
)

from flask import Blueprint, request, current_app, render_template, flash, Response, session, redirect, url_for, abort
from flask_login import login_required, current_user, login_user

from app.auth.controllers import log_login_to_database
from app.auth.models import User
from app.database.database import db
from app.forms import CredentialForm
from app.webauthn.models import WebauthnCredential
from app import csrf
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import os


APP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(APP_PATH, 'templates/webauthn')

webauthn_bp = Blueprint("webauthn", __name__, url_prefix='/webauthn', template_folder=TEMPLATE_PATH)

WEBAUTHN_RP_ID = os.environ["WEBAUTHN_RP_ID"]
WEBAUTHN_ORIGIN = os.environ["WEBAUTHN_ORIGIN"]
WEBAUTHN_RP_NAME = os.environ["WEBAUTHN_RP_NAME"]


@webauthn_bp.route("/")
@login_required
@csrf.exempt
def webauthn_index():
    return render_template("webauthn.html")


@webauthn_bp.route("/login")
@csrf.exempt
def webauthn_login():
    if current_user.is_authenticated:
        return redirect(url_for("webauthn.webauthn_index"))
    else:
        return render_template("webauthn.html")


def generate_random_opaque_bytes(length):
    # Generate random bytes using secrets module
    random_bytes = secrets.token_bytes(int(length/2)-2)
    return random_bytes.hex()


def is_unique_user_handle(_id):
    existing_record = db.session.execute(
        db.select(WebauthnCredential)
    .where(WebauthnCredential.user_handle == _id)).first()
    return existing_record is None


def generate_unique_user_handle(length=None):
    while True:
        unique_id = generate_random_opaque_bytes(length)
        if is_unique_user_handle(unique_id):
            print("User handle:")
            print(unique_id)
            print(f"Length: {len(unique_id)}")
            utf_encoded = unique_id.encode("utf-8")
            print(f"UTF-8 encoded length: {len(utf_encoded)}")
            return unique_id


@webauthn_bp.route("/registration-options")
@login_required
@csrf.exempt
def handler_generate_registration_options():
    exclude_credentials = None
    if current_user.webauthn_credentials is not None:
        exclude_credentials = [
            {"id": cred.id, "transports": cred.transports, "type": "public-key"}
            for cred in current_user.webauthn_credentials
        ]
    user_id = db.session.execute(
        db.select(WebauthnCredential.user_handle)
        .where(WebauthnCredential.rp_user_id == current_user.id)
    ).scalar()
    if user_id is None:
        user_id = generate_unique_user_handle(64)
    options = generate_registration_options(
        rp_name=WEBAUTHN_RP_NAME, # A name for your "Relying Party" server
        rp_id=WEBAUTHN_RP_ID, # Your domain on which WebAuthn is being used
        user_id=user_id, #current_user.id), # An assigned random identifier
        user_name=current_user.email,# A user-visible hint of which account this credential belongs to
        exclude_credentials=exclude_credentials,
        # Require the user to verify their identity to the authenticator
        authenticator_selection=AuthenticatorSelectionCriteria(
            user_verification=UserVerificationRequirement.REQUIRED,
            resident_key=ResidentKeyRequirement.REQUIRED
        ),
    )
    # Remember the challenge for later, you'll need it in the next step
    session["current_challenge"] = options.challenge
    session["rp_user_id"] = user_id

    options_json_string = options_to_json(options)
    options_json = json.loads(options_json_string)
    options_json["user"]["id"] = user_id
    options_json_string = json.dumps(options_json)
    return options_json_string


@webauthn_bp.post("/registration-verification")
@login_required
@csrf.exempt
def handler_verify_registration_response():
    body = request.get_data()
    try:
        credential = RegistrationCredential.model_validate_json(body)
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=session["current_challenge"],
            expected_rp_id=WEBAUTHN_RP_ID,
            expected_origin=WEBAUTHN_ORIGIN,
            require_user_verification=True,
        )
    except Exception as err:
        return {"verified": False, "msg": str(err), "status": 400}

    new_credential = WebauthnCredential(
        id=verification.credential_id,
        public_key=verification.credential_public_key,
        user_handle=session["rp_user_id"],
        rp_user_id=current_user.id,
        sign_count=verification.sign_count,
        transports=json.loads(body).get("transports", []),
    )
    if not new_credential.transports:
        new_credential.transports = None

    try:
        db.session.add(new_credential)
        db.session.commit()
        print("added new credential")
    except IntegrityError:
        # The credential_id was already taken, which caused the
        # commit to fail. Show a validation error.
        return f"Credentials {verification.credential_id} is already registered."

    print("verified")
    entry_id = new_credential.entry_id
    form = CredentialForm()
    return render_template("name_security_key.html", entry_id=entry_id, form=form)


################
#
# Authentication
#
################


@webauthn_bp.post("/authentication-options")
@csrf.exempt
def handler_generate_authentication_options():
    data = request.get_json()
    allow_credentials = None
    user = db.session.execute(
        db.select(User)
        .where(User.email == data["email"])
    ).scalar()

    if user is not None and user.webauthn_credentials is not None:
        allow_credentials = [
            {"type": "public-key",
             "id": cred.id,
             "transports": cred.transports}
            for cred in user.webauthn_credentials
        ]
        # wishes_json = {}
        # for wish in wishes:
        #     wishes_json[wish.id] = {"title": wish.title}
        #     break

    options = generate_authentication_options(
        rp_id=WEBAUTHN_RP_ID,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.REQUIRED,
    )

    session["current_challenge"] = options.challenge

    options_json = options_to_json(options)

    return options_json


@webauthn_bp.post("/authentication-verification")
@csrf.exempt
def handler_verify_authentication_response():
    body = request.get_data()
    try:
        credential = AuthenticationCredential.model_validate_json(body)

        # Find the user's corresponding public key
        # user_credential = None
        # for cred in current_user.webauthn_credentials:
        #     if cred.id == credential.raw_id:
        #         user_credential = cred
        #         break
        user_credential = db.session.execute(
            db.select(WebauthnCredential)
            .where(WebauthnCredential.id == credential.raw_id)
        ).scalar()
        if user_credential is None:
            raise Exception("Could not find corresponding public key in DB")

        # Verify the assertion
        verification = verify_authentication_response(
            credential=AuthenticationCredential.model_validate_json(request.data),
            expected_challenge=session["current_challenge"],
            expected_rp_id=WEBAUTHN_RP_ID,
            expected_origin=WEBAUTHN_ORIGIN,
            credential_public_key=user_credential.public_key,
            credential_current_sign_count=user_credential.sign_count,
            require_user_verification=True,
        )
    except Exception as err:
        return {"verified": False, "msg": str(err), "status": 400}

    # Update our credential's sign count to what the authenticator says it is now
    user_credential.sign_count = verification.new_sign_count
    db.session.commit()

    login_user(user_credential.user)
    log_login_to_database(user_credential.rp_user_id, "security_key", user_credential.entry_id)

    return {"verified": True, "redirect": url_for("wishlist.index")}


def verify_credential_and_owner(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        form = CredentialForm()

        if not form.validate_on_submit():
            for error in form.errors:
                print(error)
            abort(400)

        entry_id = form.entry_id.data
        credential = db.session.get(WebauthnCredential, entry_id)

        if credential is None or not credential.current_user_is_owner():
            print("Credential not found or user unauthorized")
            abort(403)

        return view_function(credential, *args, **kwargs)
    return decorated_function


@webauthn_bp.post("/update")
@login_required
@verify_credential_and_owner
def handler_update_credential(credential):
    label = request.values.get("label")
    credential.label = label
    db.session.add(credential)

    try:
        db.session.commit()

        if request.values.get("redirect") == "true":
            return redirect(url_for("auth.dashboard"))
        return "success", 200

    except SQLAlchemyError:
        abort(500)


@webauthn_bp.delete("/delete")
@login_required
@verify_credential_and_owner
def handler_delete_credential(credential):
    db.session.delete(credential)
    try:
        db.session.commit()
        return "success", 200

    except SQLAlchemyError:
        abort(500)
