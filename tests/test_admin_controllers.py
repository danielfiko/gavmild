from datetime import datetime, timezone

from app import db as _db
from app.admin.controllers import (
    delete_suggestion,
    generate_reset_link,
    get_all_suggestions,
    get_all_users,
    get_user_details,
    solve_suggestion,
    update_user,
)
from app.auth.models import PasswordResetToken, User
from app.telegram.models import Suggestion, TelegramUser


def _make_telegram_user(telegram_id: int) -> TelegramUser:
    TelegramUser.create(id=telegram_id, chat_username="bot_user")
    return _db.session.get(TelegramUser, telegram_id)


def _make_suggestion(telegram_id: int, text: str = "Forslag tekst") -> Suggestion:
    Suggestion.create(user_id=telegram_id, suggestion=text)
    _db.session.commit()
    return (
        _db.session.execute(_db.select(Suggestion).order_by(Suggestion.id.desc()))
        .scalars()
        .first()
    )


class TestGetAllUsers:
    def test_returns_all_users(self, sample_user: User, other_user: User) -> None:
        users = get_all_users()
        emails = {u.email for u in users}
        assert "test@example.com" in emails
        assert "other@example.com" in emails

    def test_ordered_by_first_name(self, sample_user: User, other_user: User) -> None:
        users = get_all_users()
        names = [u.first_name for u in users]
        assert names == sorted(names)

    def test_empty_db_returns_empty_list(self) -> None:
        assert get_all_users() == []


class TestGetUserDetails:
    def test_returns_user_for_valid_id(self, sample_user: User) -> None:
        user = get_user_details(sample_user.id)
        assert user is not None
        assert user.email == "test@example.com"

    def test_returns_none_for_missing_id(self) -> None:
        assert get_user_details(9999) is None


class TestUpdateUser:
    def test_updates_user_fields(self, sample_user: User) -> None:
        result = update_user(
            user_id=sample_user.id,
            first_name="updated",
            last_name="name",
            email="UPDATED@EXAMPLE.COM",
            is_admin=True,
            force_pw_change=True,
        )
        assert result["ok"] is True

        user = _db.session.get(User, sample_user.id)
        assert user.first_name == "Updated"
        assert user.last_name == "Name"
        assert user.email == "updated@example.com"
        assert user.is_admin is True
        assert user.force_pw_change is True

    def test_returns_error_for_missing_user(self) -> None:
        result = update_user(
            user_id=9999,
            first_name="X",
            last_name="Y",
            email="x@example.com",
            is_admin=False,
            force_pw_change=False,
        )
        assert result["ok"] is False
        assert "error" in result


class TestGenerateResetLink:
    def test_returns_ok_and_url_for_valid_user(self, sample_user: User) -> None:
        result = generate_reset_link(sample_user.id)
        assert result["ok"] is True
        assert "url" in result
        assert "name" in result
        assert "bytt-passord" in result["url"]

    def test_token_persisted_with_15_min_ttl(self, sample_user: User) -> None:
        generate_reset_link(sample_user.id)
        now = datetime.now(timezone.utc)
        token = (
            _db.session.execute(
                _db.select(PasswordResetToken).where(
                    PasswordResetToken.user_id == sample_user.id
                )
            )
            .scalars()
            .first()
        )
        assert token is not None
        # Should expire in ~15 minutes
        delta_seconds = (
            token.expires_at.replace(tzinfo=timezone.utc) - now
        ).total_seconds()
        assert 800 <= delta_seconds <= 910

    def test_returns_error_for_missing_user(self) -> None:
        result = generate_reset_link(9999)
        assert result["ok"] is False
        assert "error" in result


class TestGetAllSuggestions:
    def test_returns_open_suggestions_by_default(self) -> None:
        _make_telegram_user(101)
        _make_suggestion(101, "Open suggestion")
        suggestions = get_all_suggestions()
        assert len(suggestions) >= 1
        assert all(s.solved_at is None and s.deleted_at is None for s in suggestions)

    def test_all_filter_includes_solved(self) -> None:
        _make_telegram_user(102)
        s = _make_suggestion(102, "To solve")
        s.solved_at = datetime.now(timezone.utc)
        _db.session.commit()

        all_suggestions = get_all_suggestions(filter="all")
        ids = [sg.id for sg in all_suggestions]
        assert s.id in ids

    def test_solved_filter_excludes_open(self) -> None:
        _make_telegram_user(103)
        open_s = _make_suggestion(103, "Still open")
        solved_suggestions = get_all_suggestions(filter="solved")
        ids = [sg.id for sg in solved_suggestions]
        assert open_s.id not in ids


class TestSolveSuggestion:
    def test_sets_solved_at_timestamp(self) -> None:
        _make_telegram_user(201)
        s = _make_suggestion(201, "Fix this")
        result = solve_suggestion(s.id)
        assert result["ok"] is True
        _db.session.refresh(s)
        assert s.solved_at is not None

    def test_returns_error_for_missing_suggestion(self) -> None:
        result = solve_suggestion(9999)
        assert result["ok"] is False
        assert "error" in result


class TestDeleteSuggestion:
    def test_sets_deleted_at_timestamp(self) -> None:
        _make_telegram_user(301)
        s = _make_suggestion(301, "Delete me")
        result = delete_suggestion(s.id)
        assert result["ok"] is True
        _db.session.refresh(s)
        assert s.deleted_at is not None

    def test_returns_error_for_missing_suggestion(self) -> None:
        result = delete_suggestion(9999)
        assert result["ok"] is False
        assert "error" in result
