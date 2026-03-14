import secrets
from functools import wraps

from flask import (
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import (
    parse_authentication_credential_json,
    parse_registration_credential_json,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialType,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app import csrf, db
from app.auth.controllers import log_user_login
from app.auth.models import User
from app.forms import CredentialForm
from app.webauthn import webauthn_bp
from app.webauthn.models import WebauthnCredential


@webauthn_bp.route("/") #TODO: Fjerne denne?
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
            current_app.logger.debug(f"Generated User handle: {unique_id}")
            current_app.logger.debug(f"Length: {len(unique_id)}")
            utf_encoded = unique_id.encode("utf-8")
            current_app.logger.debug(f"UTF-8 encoded length: {len(utf_encoded)}")
            return unique_id


@webauthn_bp.route("/registration-options")
@login_required
@csrf.exempt
def handler_generate_registration_options():
    exclude_credentials = None
    if current_user.webauthn_credentials is not None:
        exclude_credentials = [
            PublicKeyCredentialDescriptor(id=cred.id, transports=cred.transports, type=PublicKeyCredentialType.PUBLIC_KEY)
            for cred in current_user.webauthn_credentials
        ]
    user_id = db.session.execute(
        db.select(WebauthnCredential.user_handle)
        .where(WebauthnCredential.rp_user_id == current_user.id)
    ).scalar()
    if user_id is None:
        user_id = generate_unique_user_handle(64)
    options = generate_registration_options(
        rp_name=current_app.config.get("WEBAUTHN_RP_NAME", ""), # A name for your "Relying Party" server
        rp_id=current_app.config.get("WEBAUTHN_RP_ID", ""), # Your domain on which WebAuthn is being used
        user_id=bytes.fromhex(user_id), #current_user.id), # An assigned random identifier
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

    current_app.logger.debug(f"Generated registration options: {options}")
    return options_to_json(options)


@webauthn_bp.post("/registration-verification")
@login_required
@csrf.exempt
def handler_verify_registration_response():
    body = request.get_json()
    try:
        credential = parse_registration_credential_json(body)
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=session["current_challenge"],
            expected_rp_id=current_app.config.get("WEBAUTHN_RP_ID", ""),
            expected_origin=current_app.config.get("WEBAUTHN_ORIGIN", ""),
            require_user_verification=True,
        )
    except Exception as err:
        return jsonify({"verified": False, "msg": str(err)}), 400
    
    new_credential = WebauthnCredential(
        id=verification.credential_id,
        public_key=verification.credential_public_key,
        user_handle=session["rp_user_id"],
        rp_user_id=current_user.id,
        sign_count=verification.sign_count,
        transports=body.get("transports", []),
    )
    if not new_credential.transports:
        new_credential.transports = None

    try:
        db.session.add(new_credential)
        db.session.commit()
        current_app.logger.info(f"Added new WebAuthn credential for user {current_user.id}")
    except IntegrityError:
        db.session.rollback()
        return jsonify({"verified": False, "msg": f"Credential {verification.credential_id} is already registered."}), 409

    current_app.logger.info("Registration verification successful")
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
        rp_id=current_app.config.get("WEBAUTHN_RP_ID", ""),
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.REQUIRED,
    )

    session["current_challenge"] = options.challenge

    options_json = options_to_json(options)

    return options_json


@webauthn_bp.post("/authentication-verification")
@csrf.exempt
def handler_verify_authentication_response():
    body = request.get_json()
    try:
        credential = parse_authentication_credential_json(body)

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
            credential=credential,
            expected_challenge=session["current_challenge"],
            expected_rp_id=current_app.config.get("WEBAUTHN_RP_ID", ""),
            expected_origin=current_app.config.get("WEBAUTHN_ORIGIN", ""),
            credential_public_key=user_credential.public_key,
            credential_current_sign_count=user_credential.sign_count,
            require_user_verification=True,
        )
    except Exception as err:
        return jsonify({"verified": False, "msg": str(err)}), 400

    # Update our credential's sign count to what the authenticator says it is now
    user_credential.sign_count = verification.new_sign_count
    db.session.commit()

    session.pop("current_challenge", None)
    login_user(user_credential.user)
    log_user_login(user_credential.rp_user_id, "security_key", user_credential.entry_id)

    return jsonify({"verified": True, "redirect": url_for("wishlist.index")})


def verify_credential_and_owner(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        form = CredentialForm()

        if not form.validate_on_submit():
            for field, errors in form.errors.items():
                for error in errors:
                    current_app.logger.warning(f"Form validation error in {field}: {error}")
            abort(400)

        entry_id = form.entry_id.data
        credential = db.session.get(WebauthnCredential, entry_id)

        if credential is None or not credential.current_user_is_owner():
            current_app.logger.warning(f"Unauthorized credential access attempt. Credential ID: {entry_id}, User ID: {current_user.id if current_user.is_authenticated else 'Unauthenticated'}")
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
        db.session.rollback()
        abort(500)
