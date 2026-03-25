from flask import Flask
from flask.testing import FlaskClient

from app.auth.models import User

# run test: uv run pytest -v


class TestAppFactory:
    """Verify the app factory produces a valid Flask application."""

    def test_app_is_created(self, app: Flask) -> None:
        assert app is not None

    def test_app_is_testing(self, app: Flask) -> None:
        assert app.config["TESTING"] is True

    def test_uses_sqlite_in_tests(self, app: Flask) -> None:
        assert "sqlite" in app.config["SQLALCHEMY_DATABASE_URI"]


class TestAuthRoutes:
    """Smoke tests for authentication endpoints."""

    def test_login_page_returns_200(self, client: FlaskClient) -> None:
        response = client.get("/login")
        assert response.status_code == 200

    def test_unauthenticated_dashboard_redirects(self, client: FlaskClient) -> None:
        response = client.get("/dashboard")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


class TestUserModel:
    """Basic checks for the User model."""

    def test_create_user(self, sample_user: User) -> None:
        assert sample_user.id is not None
        assert sample_user.username == "testuser"
        assert sample_user.email == "test@example.com"
        assert sample_user.first_name == "Test"

    def test_user_repr(self, sample_user: User) -> None:
        assert "testuser" in repr(sample_user)
