import logging
import os
from datetime import datetime, timedelta, timezone

import requests
from flask import Flask
from sqlalchemy import or_

from app import db
from app.wishlist.image_generation import generate_image
from app.wishlist.models import Wish, WishList

logger = logging.getLogger(__name__)

_DEFAULT_IMG_SUFFIXES = ("gift-default.png",)
_GENERATE_BATCH_SIZE = 5
_IMG_BROKEN_THRESHOLD_HOURS = 24
_HEAD_TIMEOUT_SECONDS = 5


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


def generate_missing_wish_images(app: Flask) -> None:
    """Generate AI images for wishes that have no real image yet, and verify
    previously-broken external images.

    Pass A — Broken image verification:
      Fetches HEAD for each wish with img_broken_since set.
      - URL responds OK  → image recovered, clear img_broken_since.
      - Still broken and older than _IMG_BROKEN_THRESHOLD_HOURS → generate replacement.
      - Still broken but within threshold → leave as-is.

    Pass B — Missing image generation:
      Wishes whose img_url is NULL or a placeholder get a fresh generated image.

    Both passes are limited to _GENERATE_BATCH_SIZE wishes per run.
    """
    with app.app_context():
        _verify_broken_images()
        _generate_for_missing_images()


def _is_url_reachable(url: str) -> bool:
    """Return True if a HEAD request to url responds with status < 400."""
    try:
        response = requests.head(
            url, timeout=_HEAD_TIMEOUT_SECONDS, allow_redirects=True
        )
        return response.status_code < 400
    except requests.RequestException:
        return False


def _replace_image(wish: Wish) -> None:
    """Generate a new image for wish and update img_url. Caller must commit."""
    file_path = generate_image(
        product_name=wish.title,
        description=wish.description or "",
    )
    filename = os.path.basename(file_path)
    wish.img_url = f"/static/img/generated_images/{filename}"
    wish.img_broken_since = None
    logger.info("Generated image for wish id=%d.", wish.id)


def _verify_broken_images() -> None:
    """Pass A: verify wishes that were flagged as having a broken image URL."""
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(hours=_IMG_BROKEN_THRESHOLD_HOURS)
    try:
        wishes = (
            db.session.execute(
                db.select(Wish)
                .outerjoin(Wish.wish_list)
                .where(
                    Wish.deleted_at.is_(None),
                    Wish.img_broken_since.isnot(None),
                    Wish.img_url.isnot(None),
                    or_(Wish.list_id.is_(None), WishList.archived_at.is_(None)),
                )
                .limit(_GENERATE_BATCH_SIZE)
            )
            .scalars()
            .all()
        )
    except Exception:
        logger.exception("Error querying broken-image wishes.")
        return

    for wish in wishes:
        try:
            if _is_url_reachable(wish.img_url):
                wish.img_broken_since = None
                db.session.commit()
                logger.info("Broken image recovered for wish id=%d.", wish.id)
            elif wish.img_broken_since.replace(tzinfo=timezone.utc) <= threshold:
                _replace_image(wish)
                db.session.commit()
            # else: still broken but within threshold — leave as-is
        except Exception:
            db.session.rollback()
            logger.exception("Error processing broken image for wish id=%d.", wish.id)


def _generate_for_missing_images() -> None:
    """Pass B: generate images for wishes with no image or a placeholder."""
    default_conditions = [
        Wish.img_url.is_(None),
        *[Wish.img_url.endswith(suffix) for suffix in _DEFAULT_IMG_SUFFIXES],
    ]
    try:
        wishes = (
            db.session.execute(
                db.select(Wish)
                .outerjoin(Wish.wish_list)
                .where(
                    Wish.deleted_at.is_(None),
                    or_(Wish.list_id.is_(None), WishList.archived_at.is_(None)),
                    or_(*default_conditions),
                )
                .limit(_GENERATE_BATCH_SIZE)
            )
            .scalars()
            .all()
        )
    except Exception:
        logger.exception("Error querying wishes for image generation.")
        return

    for wish in wishes:
        try:
            _replace_image(wish)
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception("Failed to generate image for wish id=%d.", wish.id)
