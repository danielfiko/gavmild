import logging
from datetime import datetime, timezone

from flask import Flask

from app import db
from app.wishlist.models import WishList

logger = logging.getLogger(__name__)


def archive_expired_lists(app: Flask) -> None:
    """Set archived_at on all WishLists whose expires_at has passed.

    Runs as a periodic APScheduler job.  Uses a single batch UPDATE so that
    multiple lists expiring simultaneously are handled atomically.
    """
    with app.app_context():
        try:
            now = datetime.now(timezone.utc)
            result = db.session.execute(
                db.update(WishList)
                .where(WishList.expires_at <= now, WishList.archived_at.is_(None))
                .values(archived_at=now)
            )
            db.session.commit()
            if result.rowcount:
                logger.info("Archived %d expired wish list(s).", result.rowcount)
        except Exception:
            db.session.rollback()
            logger.exception("Error while archiving expired wish lists.")
