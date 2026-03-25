from unittest.mock import patch

from flask.testing import FlaskClient

from app import db as _db
from app.auth.models import User


# Routes to test (all behind /admin prefix)
ADMIN_ROUTES = [
    "/admin/",
    "/admin/users",
    "/admin/suggestions",
    "/admin/telegram",
]


class TestAdminUnauthenticated:
    """Unauthenticated users must be redirected to /login for all admin routes."""

    def test_index_redirects_to_login(self, client: FlaskClient) -> None:
        response = client.get("/admin/")
        assert response.status_code == 302
        assert "login" in response.headers.get("Location", "")

    def test_users_redirects_to_login(self, client: FlaskClient) -> None:
        response = client.get("/admin/users")
        assert response.status_code == 302
        assert "login" in response.headers.get("Location", "")

    def test_suggestions_redirects_to_login(self, client: FlaskClient) -> None:
        response = client.get("/admin/suggestions")
        assert response.status_code == 302
        assert "login" in response.headers.get("Location", "")

    def test_telegram_redirects_to_login(self, client: FlaskClient) -> None:
        response = client.get("/admin/telegram")
        assert response.status_code == 302
        assert "login" in response.headers.get("Location", "")


class TestAdminNonAdmin:
    """Non-admin users must receive 403 for all admin routes."""

    def test_index_returns_403(self, logged_in_client: FlaskClient) -> None:
        response = logged_in_client.get("/admin/")
        assert response.status_code == 403

    def test_users_returns_403(self, logged_in_client: FlaskClient) -> None:
        response = logged_in_client.get("/admin/users")
        assert response.status_code == 403

    def test_suggestions_returns_403(self, logged_in_client: FlaskClient) -> None:
        response = logged_in_client.get("/admin/suggestions")
        assert response.status_code == 403

    def test_post_user_update_returns_403(
        self, logged_in_client: FlaskClient, sample_user: User
    ) -> None:
        response = logged_in_client.post(
            f"/admin/users/{sample_user.id}/update",
            data={
                "first_name": "Hacked",
                "last_name": "User",
                "email": "hacked@example.com",
            },
        )
        assert response.status_code == 403


class TestAdminAccess:
    """Admin users can access all admin routes (template rendering is mocked to avoid
    MySQL-specific SQL functions that are incompatible with SQLite in tests)."""

    def test_index_returns_200(self, admin_client: FlaskClient) -> None:
        with patch("app.admin.routes.logged_in_content", return_value="OK"):
            response = admin_client.get("/admin/")
        assert response.status_code == 200

    def test_users_returns_200(
        self, admin_client: FlaskClient, sample_user: User
    ) -> None:
        with patch("app.admin.routes.logged_in_content", return_value="OK"):
            response = admin_client.get("/admin/users")
        assert response.status_code == 200

    def test_suggestions_returns_200(self, admin_client: FlaskClient) -> None:
        with patch("app.admin.routes.logged_in_content", return_value="OK"):
            response = admin_client.get("/admin/suggestions")
        assert response.status_code == 200

    def test_user_update_redirects_after_success(
        self, admin_client: FlaskClient, sample_user: User
    ) -> None:
        response = admin_client.post(
            f"/admin/users/{sample_user.id}/update",
            data={
                "first_name": "Updated",
                "last_name": "Name",
                "email": "updated@example.com",
            },
        )
        assert response.status_code == 302

        user = _db.session.get(User, sample_user.id)
        assert user.first_name == "Updated"

    def test_user_update_missing_user_returns_redirect(
        self, admin_client: FlaskClient
    ) -> None:
        response = admin_client.post(
            "/admin/users/9999/update",
            data={
                "first_name": "Ghost",
                "last_name": "User",
                "email": "ghost@example.com",
            },
        )
        # Route redirects back to user detail page (which would 404, but the redirect itself is 302)
        assert response.status_code == 302
