from app import db as _db
from app.auth.models import User
from app.telegram.controllers import (
    svc_add_suggestion,
    svc_connect_user,
    svc_delete_suggestion,
    svc_get_users,
    svc_solve_suggestion,
    unlink_telegram_user,
)
from app.telegram.models import Suggestion, TelegramUser, TelegramUserConnection


class TestSvcAddSuggestion:
    def test_creates_telegram_user_and_suggestion(self) -> None:
        result = svc_add_suggestion(
            username="tguser", user_id=999, suggestion_text="This is a suggestion"
        )
        assert result is True

        tg_user = _db.session.get(TelegramUser, 999)
        assert tg_user is not None
        assert tg_user.chat_username == "tguser"

        suggestion = (
            _db.session.execute(_db.select(Suggestion).where(Suggestion.user_id == 999))
            .scalars()
            .first()
        )
        assert suggestion is not None
        assert suggestion.suggestion == "This is a suggestion"

    def test_updates_username_for_existing_telegram_user(self) -> None:
        TelegramUser.create(id=998, chat_username="oldname")
        _db.session.commit()

        svc_add_suggestion(
            username="newname", user_id=998, suggestion_text="Update test"
        )

        tg_user = _db.session.get(TelegramUser, 998)
        assert tg_user.chat_username == "newname"


class TestSvcDeleteSuggestion:
    def _setup(self) -> Suggestion:
        TelegramUser.create(id=500, chat_username="deleter")
        _db.session.commit()
        Suggestion.create(user_id=500, suggestion="Delete me")
        _db.session.commit()
        return (
            _db.session.execute(_db.select(Suggestion).order_by(Suggestion.id.desc()))
            .scalars()
            .first()
        )

    def test_soft_deletes_suggestion(self) -> None:
        s = self._setup()
        result = svc_delete_suggestion(str(s.id))
        assert result["ok"] is True
        _db.session.refresh(s)
        assert s.deleted_at is not None

    def test_returns_not_found_for_missing_id(self) -> None:
        result = svc_delete_suggestion("9999")
        assert result["ok"] is False
        assert result.get("not_found") is True


class TestSvcSolveSuggestion:
    def _setup(self) -> Suggestion:
        TelegramUser.create(id=600, chat_username="solver")
        _db.session.commit()
        Suggestion.create(user_id=600, suggestion="Solve me")
        _db.session.commit()
        return (
            _db.session.execute(_db.select(Suggestion).order_by(Suggestion.id.desc()))
            .scalars()
            .first()
        )

    def test_marks_suggestion_solved(self) -> None:
        s = self._setup()
        result = svc_solve_suggestion(str(s.id))
        assert result["ok"] is True
        _db.session.refresh(s)
        assert s.solved_at is not None

    def test_returns_not_found_for_missing_id(self) -> None:
        result = svc_solve_suggestion("9999")
        assert result["ok"] is False
        assert result.get("not_found") is True


class TestSvcConnectUser:
    def test_links_telegram_user_to_webapp_user(self, sample_user: User) -> None:
        TelegramUserConnection.create(
            user_id=sample_user.id, identifier="abc123"
        )
        _db.session.commit()

        result = svc_connect_user(
            chat_user_id=700, chat_username="linker", identifier="abc123"
        )
        assert result["ok"] is True
        assert "username" in result

        # Connection code should be consumed
        assert _db.session.get(TelegramUserConnection, "abc123") is None

    def test_returns_not_found_for_invalid_code(self) -> None:
        result = svc_connect_user(
            chat_user_id=701, chat_username="nobody", identifier="invalid"
        )
        assert result["ok"] is False
        assert result.get("not_found") is True


class TestSvcGetUsers:
    def test_returns_list_of_dicts(self, sample_user: User) -> None:
        users = svc_get_users()
        assert users is not None
        assert isinstance(users, list)
        assert len(users) >= 1
        assert "id" in users[0]
        assert "first_name" in users[0]

    def test_empty_db_returns_empty_list(self) -> None:
        result = svc_get_users()
        assert result == []


class TestUnlinkTelegramUser:
    def test_sets_user_id_to_none(self, sample_user: User) -> None:
        TelegramUser.create(id=800, chat_username="linked", user_id=sample_user.id)
        _db.session.commit()

        result = unlink_telegram_user(800)
        assert result["ok"] is True

        tg = _db.session.get(TelegramUser, 800)
        assert tg.user_id is None

    def test_returns_error_for_missing_telegram_user(self) -> None:
        result = unlink_telegram_user(9999)
        assert result["ok"] is False
        assert "error" in result
