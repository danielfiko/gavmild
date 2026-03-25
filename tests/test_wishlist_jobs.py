from datetime import datetime, timedelta, timezone

from flask import Flask

from app import db as _db
from app.auth.models import User
from app.wishlist.jobs import archive_expired_lists
from app.wishlist.models import WishList


def _make_list(
    user_id: int, expires_offset_days: int, archived_at: datetime | None = None
) -> WishList:
    wl = WishList(
        user_id=user_id,
        title="Test list",
        expires_at=datetime.now(timezone.utc) + timedelta(days=expires_offset_days),
        archived_at=archived_at,
    )
    _db.session.add(wl)
    _db.session.commit()
    return wl


class TestArchiveExpiredLists:
    def test_archives_expired_list(self, app: Flask, sample_user: User) -> None:
        wl = _make_list(user_id=sample_user.id, expires_offset_days=-1)
        assert wl.archived_at is None

        archive_expired_lists(app)

        _db.session.expire(wl)
        wl = _db.session.get(WishList, wl.id)
        assert wl.archived_at is not None

    def test_does_not_archive_future_list(self, app: Flask, sample_user: User) -> None:
        wl = _make_list(user_id=sample_user.id, expires_offset_days=30)

        archive_expired_lists(app)

        _db.session.expire(wl)
        wl = _db.session.get(WishList, wl.id)
        assert wl.archived_at is None

    def test_does_not_re_archive_already_archived_list(
        self, app: Flask, sample_user: User
    ) -> None:
        # Store a naive datetime — SQLite strips timezone info on read-back
        original_ts = datetime(2025, 1, 1)
        wl = _make_list(
            user_id=sample_user.id,
            expires_offset_days=-10,
            archived_at=original_ts,
        )

        archive_expired_lists(app)

        _db.session.expire(wl)
        wl = _db.session.get(WishList, wl.id)
        assert wl.archived_at == original_ts

    def test_archives_multiple_expired_lists(
        self, app: Flask, sample_user: User
    ) -> None:
        wl1 = _make_list(user_id=sample_user.id, expires_offset_days=-2)
        wl2 = _make_list(user_id=sample_user.id, expires_offset_days=-5)

        archive_expired_lists(app)

        _db.session.expire(wl1)
        _db.session.expire(wl2)
        wl1 = _db.session.get(WishList, wl1.id)
        wl2 = _db.session.get(WishList, wl2.id)
        assert wl1.archived_at is not None
        assert wl2.archived_at is not None
