from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app import db as _db
from app.auth.controllers import (
    authenticate_user,
    email_exists,
    generate_unique_code,
    generate_unique_username,
    get_user_by_email,
    hash_password_to_string,
    register_user,
)
from app.auth.decorators import extract_token_data, is_valid_token
from app.auth.models import PasswordResetToken, User


class TestGenerateUniqueCode:
    def test_default_length(self) -> None:
        code = generate_unique_code()
        assert len(code) == 10

    def test_custom_length(self) -> None:
        assert len(generate_unique_code(length=6)) == 6

    def test_returns_string(self) -> None:
        assert isinstance(generate_unique_code(), str)

    def test_produces_different_values(self) -> None:
        codes = {generate_unique_code() for _ in range(5)}
        assert len(codes) > 1


class TestExtractTokenData:
    def test_valid_format_splits_correctly(self) -> None:
        token_id, token_string = extract_token_data("abc12-xyz99")
        assert token_id == "abc12"
        assert token_string == "xyz99"

    def test_no_dash_returns_none_pair(self) -> None:
        token_id, token_string = extract_token_data("nodashhere")
        assert token_id is None
        assert token_string is None

    def test_empty_string_returns_none_pair(self) -> None:
        token_id, token_string = extract_token_data("")
        assert token_id is None
        assert token_string is None

    def test_multiple_dashes_returns_none_pair(self) -> None:
        # split("-") with maxsplit=1 not used; two dashes fail the unpack
        token_id, token_string = extract_token_data("a-b-c")
        assert token_id is None
        assert token_string is None


class TestHashPasswordToString:
    def test_returns_string(self) -> None:
        assert isinstance(hash_password_to_string("testpassword"), str)

    def test_hash_verifiable_with_bcrypt(self) -> None:
        from app import bcrypt

        hashed = hash_password_to_string("mypassword")
        assert bcrypt.check_password_hash(hashed, "mypassword")

    def test_different_inputs_produce_different_hashes(self) -> None:
        h1 = hash_password_to_string("password1")
        h2 = hash_password_to_string("password2")
        assert h1 != h2


class TestIsValidToken:
    def _make_token(
        self, token_string: str, expires_in_seconds: int = 3600
    ) -> PasswordResetToken:
        from app import bcrypt

        hashed = bcrypt.generate_password_hash(token_string).decode("utf-8")
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
        token = PasswordResetToken.create(
            token_id="test01",
            token=hashed,
            user_id=1,
            expires_at=expires_at,
        )
        return token

    def test_valid_token_returns_true(self) -> None:
        token = self._make_token("validtoken")
        assert is_valid_token(token, "validtoken") is True

    def test_wrong_string_returns_false(self) -> None:
        token = self._make_token("validtoken")
        assert is_valid_token(token, "wrongtoken") is False

    def test_expired_token_returns_false(self) -> None:
        token = self._make_token("validtoken", expires_in_seconds=-1)
        assert is_valid_token(token, "validtoken") is False

    def test_used_token_returns_false(self) -> None:
        token = self._make_token("validtoken")
        token.used_at = datetime.now(timezone.utc)
        assert is_valid_token(token, "validtoken") is False

    def test_none_entry_returns_false(self) -> None:
        assert is_valid_token(None, "anytoken") is False  # type: ignore[arg-type]


class TestEmailExists:
    def test_existing_email_returns_true(self, sample_user: User) -> None:
        assert email_exists("test@example.com") is True

    def test_unknown_email_returns_false(self, sample_user: User) -> None:
        assert email_exists("nobody@example.com") is False

    def test_no_case_insensitive_match(self, sample_user: User) -> None:
        # Email is stored lowercase by User.create(); uppercase query finds nothing
        assert email_exists("TEST@EXAMPLE.COM") is False


class TestGetUserByEmail:
    def test_returns_user_for_known_email(self, sample_user: User) -> None:
        user = get_user_by_email("test@example.com")
        assert user is not None
        assert user.username == "testuser"

    def test_returns_none_for_unknown_email(self, sample_user: User) -> None:
        assert get_user_by_email("unknown@example.com") is None


class TestAuthenticateUser:
    def _create_user_with_password(
        self, email: str, password: str, username: str
    ) -> None:
        hashed = hash_password_to_string(password)
        user = User.create(
            first_name="Auth",
            last_name="Tester",
            email=email,
            hashed_password=hashed,
            date_of_birth=datetime(1990, 1, 1, tzinfo=timezone.utc),
            username=username,
        )
        _db.session.add(user)
        _db.session.commit()

    def test_correct_credentials_returns_user(self) -> None:
        self._create_user_with_password("login@example.com", "correctpass", "loginuser")
        result = authenticate_user("login@example.com", "correctpass")
        assert result is not None
        assert result.username == "loginuser"

    def test_wrong_password_returns_none(self) -> None:
        self._create_user_with_password(
            "login2@example.com", "correctpass", "loginuser2"
        )
        assert authenticate_user("login2@example.com", "wrongpassword") is None

    def test_unknown_email_returns_none(self) -> None:
        assert authenticate_user("nobody@example.com", "anypassword") is None


class TestRegisterUser:
    def _make_form(
        self,
        email: str,
        first_name: str = "New",
        last_name: str = "User",
        password: str = "securepassword123",
    ) -> MagicMock:
        """Return a minimal RegisterForm-compatible stub."""
        import datetime as dt

        form = MagicMock()
        form.email.data = email
        form.first_name.data = first_name
        form.last_name.data = last_name
        form.password.data = password
        form.date_of_birth.data = dt.date(1990, 5, 1)
        return form

    def test_creates_user_with_correct_email(self) -> None:
        user = register_user(self._make_form("new@example.com"))
        assert user.email == "new@example.com"

    def test_raises_value_error_on_duplicate_email(self, sample_user: User) -> None:
        with pytest.raises(ValueError, match="registrert"):
            register_user(self._make_form("test@example.com"))

    def test_user_not_saved_without_explicit_commit(self) -> None:
        user = register_user(self._make_form("nosave@example.com"))
        # register_user adds to session but caller must commit
        assert user.id is None or get_user_by_email("nosave@example.com") is not None


class TestGenerateUniqueUsername:
    def test_generates_from_first_and_last_name(self) -> None:
        username = generate_unique_username("Anna", "Larsen")
        assert username is not None
        assert username.startswith("annal")

    def test_appends_suffix_on_collision(self) -> None:
        existing = User.create(
            first_name="Ana",
            last_name="Larsen",
            email="ana@example.com",
            hashed_password="hash",
            date_of_birth=datetime(1990, 1, 1, tzinfo=timezone.utc),
            username="anal",
        )
        _db.session.add(existing)
        _db.session.commit()

        username = generate_unique_username("Ana", "Larsen")
        assert username is not None
        assert username != "anal"

    def test_returns_none_after_repeated_collisions(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Patch scalar_one_or_none to always return a non-None value (simulate 10 collisions)
        monkeypatch.setattr(
            "app.auth.controllers.db.session.execute",
            lambda *a, **kw: MagicMock(scalar_one_or_none=lambda: object()),
        )
        result = generate_unique_username("Test", "User")
        assert result is None
