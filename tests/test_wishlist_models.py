from datetime import datetime, timedelta, timezone

from flask import Flask

from app import db as _db
from app.auth.models import User
from app.wishlist.models import ClaimedWish, Wish, WishList


class TestWishListIsActive:
    def test_active_when_archived_at_is_none(self) -> None:
        wl = WishList(
            user_id=1,
            title="Active list",
            expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        )
        assert wl.is_active() is True

    def test_inactive_when_archived_at_is_set(self) -> None:
        wl = WishList(
            user_id=1,
            title="Archived list",
            expires_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            archived_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
        )
        assert wl.is_active() is False


class TestWishTimeSinceCreation:
    def _make_wish(self, user_id: int, date_created: datetime) -> Wish:
        wish = Wish(
            user_id=user_id,
            title="Timed wish",
            quantity=1,
            date_created=date_created,
        )
        _db.session.add(wish)
        _db.session.commit()
        return wish

    def test_today_produces_i_dag(self, sample_user: User) -> None:
        wish = self._make_wish(
            user_id=sample_user.id,
            date_created=datetime.utcnow(),
        )
        assert wish.time_since_creation() == "i dag"

    def test_one_day_ago_produces_dag_siden(self, sample_user: User) -> None:
        wish = self._make_wish(
            user_id=sample_user.id,
            date_created=datetime.utcnow() - timedelta(days=1),
        )
        assert "dag siden" in wish.time_since_creation()

    def test_multiple_days_produces_dager_siden(self, sample_user: User) -> None:
        wish = self._make_wish(
            user_id=sample_user.id,
            date_created=datetime.utcnow() - timedelta(days=5),
        )
        assert "dager siden" in wish.time_since_creation()

    def test_more_than_one_month_produces_maned(self, sample_user: User) -> None:
        wish = self._make_wish(
            user_id=sample_user.id,
            date_created=datetime.utcnow() - timedelta(days=40),
        )
        result = wish.time_since_creation()
        assert "måned" in result

    def test_more_than_one_year_produces_ar_siden(self, sample_user: User) -> None:
        wish = self._make_wish(
            user_id=sample_user.id,
            date_created=datetime(2022, 1, 1),
        )
        assert "år siden" in wish.time_since_creation()


class TestWishIsClaimedByUser:
    def test_returns_false_when_no_claims(self, sample_user: User) -> None:
        wish = Wish(user_id=sample_user.id, title="Unclaimed", quantity=1)
        _db.session.add(wish)
        _db.session.commit()

        wish = _db.session.get(Wish, wish.id)
        assert wish.is_claimed_by_user(sample_user.id) is False

    def test_returns_true_for_claiming_user(
        self, sample_user: User, other_user: User
    ) -> None:
        wish = Wish(user_id=sample_user.id, title="Claimed wish", quantity=1)
        _db.session.add(wish)
        _db.session.commit()

        claim = ClaimedWish(wish_id=wish.id, user_id=other_user.id, quantity=1)
        _db.session.add(claim)
        _db.session.commit()

        wish = _db.session.get(Wish, wish.id)
        assert wish.is_claimed_by_user(other_user.id) is True

    def test_returns_false_for_non_claiming_user(
        self, sample_user: User, other_user: User
    ) -> None:
        wish = Wish(user_id=sample_user.id, title="Claimed by other", quantity=1)
        _db.session.add(wish)
        _db.session.commit()

        claim = ClaimedWish(wish_id=wish.id, user_id=other_user.id, quantity=1)
        _db.session.add(claim)
        _db.session.commit()

        wish = _db.session.get(Wish, wish.id)
        assert wish.is_claimed_by_user(sample_user.id) is False


class TestWishTojson:
    def test_own_wish_has_claimed_zero(self, app: Flask, sample_user: User) -> None:
        wish = Wish(user_id=sample_user.id, title="My wish", quantity=1)
        _db.session.add(wish)
        _db.session.commit()

        user = _db.session.get(User, sample_user.id)
        wish = _db.session.get(Wish, wish.id)

        with app.test_request_context():
            from flask_login import login_user

            login_user(user)
            result = wish.tojson()

        assert result["claimed"] == 0

    def test_unclaimed_other_wish_has_claimed_three(
        self, app: Flask, sample_user: User, other_user: User
    ) -> None:
        wish = Wish(user_id=other_user.id, title="Others wish", quantity=1)
        _db.session.add(wish)
        _db.session.commit()

        user = _db.session.get(User, sample_user.id)
        wish = _db.session.get(Wish, wish.id)

        with app.test_request_context():
            from flask_login import login_user

            login_user(user)
            result = wish.tojson()

        assert result["claimed"] == 3

    def test_claimed_by_me_has_claimed_one(
        self, app: Flask, sample_user: User, other_user: User
    ) -> None:
        wish = Wish(user_id=other_user.id, title="I claimed this", quantity=1)
        _db.session.add(wish)
        _db.session.commit()

        claim = ClaimedWish(wish_id=wish.id, user_id=sample_user.id, quantity=1)
        _db.session.add(claim)
        _db.session.commit()

        user = _db.session.get(User, sample_user.id)
        wish = _db.session.get(Wish, wish.id)

        with app.test_request_context():
            from flask_login import login_user

            login_user(user)
            result = wish.tojson()

        assert result["claimed"] == 1

    def test_claimed_by_someone_else_has_claimed_two(
        self, app: Flask, sample_user: User, other_user: User
    ) -> None:
        third = User.create(
            first_name="Third",
            last_name="User",
            email="third@example.com",
            hashed_password="hash",
            date_of_birth=datetime(1990, 1, 1, tzinfo=timezone.utc),
            username="thirduser",
        )
        _db.session.add(third)
        _db.session.commit()

        wish = Wish(user_id=other_user.id, title="Claimed by third", quantity=1)
        _db.session.add(wish)
        _db.session.commit()

        claim = ClaimedWish(wish_id=wish.id, user_id=third.id, quantity=1)
        _db.session.add(claim)
        _db.session.commit()

        user = _db.session.get(User, sample_user.id)
        wish = _db.session.get(Wish, wish.id)

        with app.test_request_context():
            from flask_login import login_user

            login_user(user)
            result = wish.tojson()

        assert result["claimed"] == 2

    def test_tojson_contains_expected_keys(self, app: Flask, sample_user: User) -> None:
        wish = Wish(user_id=sample_user.id, title="Key check", quantity=1)
        _db.session.add(wish)
        _db.session.commit()

        user = _db.session.get(User, sample_user.id)
        wish = _db.session.get(Wish, wish.id)

        with app.test_request_context():
            from flask_login import login_user

            login_user(user)
            result = wish.tojson()

        assert "id" in result
        assert "wish_title" in result
        assert "claimed" in result
