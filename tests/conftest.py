from datetime import datetime, timezone
from typing import Generator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app, db as _db
from app.auth.models import User
from app.config import TestingConfig
from app.wishlist.models import Wish, WishList


@pytest.fixture(scope="session")
def app() -> Generator[Flask, None, None]:
    """Create the Flask application for the full test session."""
    application: Flask = create_app(config_class=TestingConfig)
    yield application


@pytest.fixture(autouse=True)
def _setup_db(app: Flask) -> Generator[None, None, None]:
    """Create tables before each test and drop them after."""
    with app.app_context():
        _db.create_all()
        yield
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """A Flask test client for sending requests."""
    return app.test_client()


@pytest.fixture()
def sample_user(app: Flask) -> User:
    """Create and persist a non-admin user for tests that need one."""
    user: User = User.create(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        hashed_password="pbkdf2:sha256:fakehash",
        date_of_birth=datetime(1990, 1, 15, tzinfo=timezone.utc),
        username="testuser",
    )
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture()
def admin_user(app: Flask) -> User:
    """Create and persist a user with admin privileges."""
    user: User = User.create(
        first_name="Admin",
        last_name="User",
        email="admin@example.com",
        hashed_password="pbkdf2:sha256:fakehash",
        date_of_birth=datetime(1985, 3, 20, tzinfo=timezone.utc),
        username="adminuser",
    )
    user.is_admin = True
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture()
def other_user(app: Flask) -> User:
    """Create and persist a second non-admin user for cross-user tests."""
    user: User = User.create(
        first_name="Other",
        last_name="Person",
        email="other@example.com",
        hashed_password="pbkdf2:sha256:fakehash",
        date_of_birth=datetime(1985, 6, 20, tzinfo=timezone.utc),
        username="otherperson",
    )
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture()
def logged_in_client(app: Flask, sample_user: User) -> FlaskClient:
    """A test client with sample_user authenticated via session."""
    test_client: FlaskClient = app.test_client()
    with test_client.session_transaction() as sess:
        sess["_user_id"] = str(sample_user.id)
        sess["_fresh"] = True
    return test_client


@pytest.fixture()
def admin_client(app: Flask, admin_user: User) -> FlaskClient:
    """A test client authenticated as the admin user."""
    test_client: FlaskClient = app.test_client()
    with test_client.session_transaction() as sess:
        sess["_user_id"] = str(admin_user.id)
        sess["_fresh"] = True
    return test_client


@pytest.fixture()
def sample_wish_list(app: Flask, sample_user: User) -> WishList:
    """An active WishList belonging to sample_user."""
    wish_list: WishList = WishList(
        user_id=sample_user.id,
        title="Test ønskeliste",
        template="birthday",
        expires_at=datetime(2027, 1, 15, tzinfo=timezone.utc),
    )
    _db.session.add(wish_list)
    _db.session.commit()
    return wish_list


@pytest.fixture()
def sample_wish(app: Flask, sample_user: User, sample_wish_list: WishList) -> Wish:
    """A Wish belonging to sample_user on sample_wish_list."""
    wish: Wish = Wish(
        user_id=sample_user.id,
        title="Test Ønske",
        quantity=1,
        list_id=sample_wish_list.id,
    )
    _db.session.add(wish)
    _db.session.commit()
    return wish
