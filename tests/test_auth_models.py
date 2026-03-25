from datetime import datetime, timedelta, timezone

from app.auth.models import PasswordResetToken, User, UserLogin, UserPreferences


class TestUserCreate:
    def test_email_is_lowercased(self) -> None:
        user = User.create(
            first_name="John",
            last_name="Doe",
            email="JOHN@EXAMPLE.COM",
            hashed_password="hash",
            date_of_birth=datetime(1990, 1, 1, tzinfo=timezone.utc),
            username="johnd",
        )
        assert user.email == "john@example.com"

    def test_names_are_title_cased(self) -> None:
        user = User.create(
            first_name="john",
            last_name="doe",
            email="john@example.com",
            hashed_password="hash",
            date_of_birth=datetime(1990, 1, 1, tzinfo=timezone.utc),
            username="johnd",
        )
        assert user.first_name == "John"
        assert user.last_name == "Doe"

    def test_password_stored_unchanged(self) -> None:
        user = User.create(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            hashed_password="myhash",
            date_of_birth=datetime(1990, 1, 1, tzinfo=timezone.utc),
            username="testuser",
        )
        assert user.password == "myhash"

    def test_does_not_assign_id_before_db_save(self) -> None:
        user = User.create(
            first_name="Test",
            last_name="User",
            email="dbtest@example.com",
            hashed_password="hash",
            date_of_birth=datetime(1990, 1, 1, tzinfo=timezone.utc),
            username="dbtestuser",
        )
        assert user.id is None


class TestUserMethods:
    def test_tojson_contains_id_and_username(self, sample_user: User) -> None:
        result = sample_user.tojson()
        assert result["id"] == sample_user.id
        assert result["username"] == sample_user.username

    def test_repr_contains_username(self, sample_user: User) -> None:
        assert "testuser" in repr(sample_user)

    def test_get_first_name_returns_first_name(self, sample_user: User) -> None:
        assert sample_user.get_first_name() == "Test"


class TestUserPreferencesCreate:
    def test_defaults_are_applied(self) -> None:
        prefs = UserPreferences.create(user_id=1)
        assert prefs.user_id == 1
        assert prefs.order_users_by is None
        assert prefs.show_claims is True

    def test_custom_values_are_stored(self) -> None:
        prefs = UserPreferences.create(
            user_id=2, order_users_by="birthday", show_claims=False
        )
        assert prefs.order_users_by == "birthday"
        assert prefs.show_claims is False


class TestPasswordResetTokenCreate:
    def test_all_fields_stored_correctly(self) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        token = PasswordResetToken.create(
            token_id="abc12",
            token="hashedtoken",
            user_id=1,
            expires_at=expires_at,
        )
        assert token.token_id == "abc12"
        assert token.token == "hashedtoken"
        assert token.user_id == 1
        assert token.expires_at == expires_at
        assert token.used_at is None

    def test_repr_contains_token_id(self) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        token = PasswordResetToken.create(
            token_id="xyz99", token="h", user_id=1, expires_at=expires_at
        )
        assert "xyz99" in repr(token)


class TestUserLoginCreate:
    def test_all_fields_stored_correctly(self) -> None:
        login = UserLogin.create(
            user_id=1,
            login_type="password",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0",
        )
        assert login.user_id == 1
        assert login.login_type == "password"
        assert login.ip_address == "127.0.0.1"
        assert login.user_agent == "Mozilla/5.0"
        assert login.credential is None

    def test_credential_id_can_be_set(self) -> None:
        login = UserLogin.create(
            user_id=1,
            login_type="security_key",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0",
            credential=42,
        )
        assert login.credential == 42
