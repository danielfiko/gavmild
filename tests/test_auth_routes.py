from datetime import datetime, timezone

from flask.testing import FlaskClient

from app import db as _db
from app.auth.controllers import hash_password_to_string
from app.auth.models import User


def _create_login_user(
    email: str = "logintest@example.com",
    password: str = "testpassword",
    username: str = "logintestuser",
) -> User:
    """Create and persist a user with a real bcrypt hash."""
    user = User.create(
        first_name="Login",
        last_name="Tester",
        email=email,
        hashed_password=hash_password_to_string(password),
        date_of_birth=datetime(1990, 1, 1, tzinfo=timezone.utc),
        username=username,
    )
    _db.session.add(user)
    _db.session.commit()
    return user


class TestLoginPage:
    def test_get_returns_200(self, client: FlaskClient) -> None:
        response = client.get("/login")
        assert response.status_code == 200

    def test_authenticated_user_is_redirected(
        self, logged_in_client: FlaskClient
    ) -> None:
        response = logged_in_client.get("/login")
        assert response.status_code == 302
        assert "login" not in response.headers.get("Location", "")


class TestRegisterPage:
    def test_get_returns_200(self, client: FlaskClient) -> None:
        response = client.get("/superhemmelig-lag-konto-side")
        assert response.status_code == 200


class TestLoginApi:
    def test_valid_credentials_redirect_to_index(self, client: FlaskClient) -> None:
        _create_login_user()
        response = client.post(
            "/api/login",
            data={"email": "logintest@example.com", "password": "testpassword"},
        )
        assert response.status_code == 302
        assert "login" not in response.headers.get("Location", "")

    def test_invalid_credentials_redirect_back_to_login(
        self, client: FlaskClient
    ) -> None:
        _create_login_user()
        response = client.post(
            "/api/login",
            data={"email": "logintest@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 302
        assert "login" in response.headers.get("Location", "")

    def test_unknown_email_redirects_to_login(self, client: FlaskClient) -> None:
        response = client.post(
            "/api/login",
            data={"email": "nobody@example.com", "password": "testpassword"},
        )
        assert response.status_code == 302
        assert "login" in response.headers.get("Location", "")

    def test_invalid_form_redirects_to_login(self, client: FlaskClient) -> None:
        # Missing password (too short)
        response = client.post(
            "/api/login",
            data={"email": "not-an-email", "password": "short"},
        )
        assert response.status_code == 302
        assert "login" in response.headers.get("Location", "")


class TestRegisterApi:
    def test_valid_registration_redirects_to_login(self, client: FlaskClient) -> None:
        response = client.post(
            "/api/register",
            data={
                "first_name": "New",
                "last_name": "Person",
                "email": "newperson@example.com",
                "password": "securepassword",
                "date_of_birth": "1990-01-15",
            },
        )
        assert response.status_code == 302
        assert "login" in response.headers.get("Location", "")

    def test_duplicate_email_returns_error_text(
        self, client: FlaskClient, sample_user: User
    ) -> None:
        response = client.post(
            "/api/register",
            data={
                "first_name": "Dupe",
                "last_name": "User",
                "email": "test@example.com",  # already exists
                "password": "securepassword",
                "date_of_birth": "1990-01-15",
            },
        )
        assert response.status_code == 200
        assert "registrert" in response.get_data(as_text=True)

    def test_invalid_form_returns_error_text(self, client: FlaskClient) -> None:
        response = client.post("/api/register", data={})
        assert response.status_code == 200


class TestLogoutApi:
    def test_unauthenticated_redirects_to_login(self, client: FlaskClient) -> None:
        response = client.post("/api/logout")
        assert response.status_code == 302
        assert "login" in response.headers.get("Location", "")

    def test_authenticated_user_is_logged_out(
        self, logged_in_client: FlaskClient
    ) -> None:
        response = logged_in_client.post("/api/logout")
        assert response.status_code == 302
        # Subsequent request should redirect to login
        follow = logged_in_client.get("/dashboard")
        assert follow.status_code == 302
        assert "login" in follow.headers.get("Location", "")


class TestChangePwApi:
    def test_valid_password_change_returns_success_text(
        self, client: FlaskClient
    ) -> None:
        _create_login_user(
            email="changepw@example.com",
            password="oldpassword",
            username="changepwuser",
        )
        response = client.post(
            "/api/change-pw",
            data={
                "email": "changepw@example.com",
                "password": "oldpassword",
                "new_password": "newpassword",
            },
        )
        assert response.status_code == 200
        assert "endret" in response.get_data(as_text=True)

    def test_wrong_old_password_returns_error_text(self, client: FlaskClient) -> None:
        _create_login_user(
            email="wrongpw@example.com",
            password="correctold",
            username="wrongpwuser",
        )
        response = client.post(
            "/api/change-pw",
            data={
                "email": "wrongpw@example.com",
                "password": "wrongold",
                "new_password": "newpassword",
            },
        )
        assert response.status_code == 200
        assert "feil" in response.get_data(as_text=True).lower()
