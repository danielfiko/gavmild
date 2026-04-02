from datetime import datetime, timezone
from typing import TYPE_CHECKING, List

from flask_login import current_user
from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db

if TYPE_CHECKING:
    from app.auth.models import User
    from app.telegram.models import ReportedLink

# TODO: Make date_created timezone-aware at the database level
#  1. Change the column to DateTime(timezone=True) (SQLAlchemy) or use auto_now_add=True (Django)
#  2. Write a migration to backfill existing rows: UPDATE table SET date_created = date_created AT TIME ZONE 'UTC'
#  3. Remove the .replace(tzinfo=timezone.utc) workaround once migration is applied


class WishList(db.Model):
    __tablename__ = "wish_list"
    __table_args__ = (Index("ix_wish_list_user_archived", "user_id", "archived_at"),)

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"), index=True)
    title: Mapped[str] = mapped_column(db.String(90), nullable=False)
    # "christmas" | "birthday" | "custom" | None (migration inbox)
    template: Mapped[str | None] = mapped_column(db.String(20))
    private: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    # Never null — enforced at the application layer
    expires_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(db.DateTime)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="lists")
    wishes: Mapped[List["Wish"]] = relationship(back_populates="wish_list")

    def is_active(self) -> bool:
        return self.archived_at is None

    def __repr__(self) -> str:
        return f"<WishList id={self.id} title={self.title!r}>"
    
    @staticmethod
    def get_active_lists(user_id: int) -> List["WishList"]:
        return list(
            db.session.execute(
                db.select(WishList)
                .where(WishList.user_id == user_id, WishList.archived_at.is_(None))
                .order_by(WishList.created_at.desc())
            )
            .scalars()
            .all()
        )


class ClaimedWish(db.Model):
    wish_id: Mapped[int] = mapped_column(
        db.Integer, ForeignKey("wish.id"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        db.Integer, ForeignKey("user.id"), primary_key=True
    )
    quantity: Mapped[int] = mapped_column(db.Integer, nullable=False)
    date: Mapped[datetime] = mapped_column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="claimed_wishes")
    wish: Mapped["Wish"] = relationship(back_populates="claims")

    def __repr__(self) -> str:
        return f"<ClaimedWish wish_id={self.wish_id} user_id={self.user_id}>"


class Wish(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    date_created: Mapped[datetime] = mapped_column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"), index=True)
    title: Mapped[str] = mapped_column(db.String(90), nullable=False)
    description: Mapped[str | None] = mapped_column(db.String(255))
    quantity: Mapped[int] = mapped_column(db.Integer, nullable=False, default=1)
    url: Mapped[str | None] = mapped_column(db.String(255))
    img_url: Mapped[str | None] = mapped_column(db.String(255))
    img_broken_since: Mapped[datetime | None] = mapped_column(db.DateTime)
    desired: Mapped[bool] = mapped_column(db.Boolean, default=0)
    price: Mapped[int | None] = mapped_column(db.Integer)
    deleted_at: Mapped[datetime | None] = mapped_column(
        db.DateTime
    )  # set = soft-deleted
    list_id: Mapped[int | None] = mapped_column(
        db.Integer, ForeignKey("wish_list.id"), index=True
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="wishes")
    claims: Mapped[List["ClaimedWish"]] = relationship(
        back_populates="wish", cascade="all, delete-orphan"
    )
    co_wishers: Mapped[List["CoWishUser"]] = relationship(
        "CoWishUser", cascade="delete"
    )
    reported_link: Mapped["ReportedLink"] = relationship(back_populates="wish")
    wish_list: Mapped["WishList | None"] = relationship(back_populates="wishes")

    def is_claimed_by_user(self, user_id):
        """Check if the wish is claimed by the specified user."""
        return any(claim.user.id == user_id for claim in self.claims)

    # TODO: Viser "i dag", dagen etter. Bør stå "i dag" og "1 dag siden"
    def time_since_creation(self):
        today = datetime.now(timezone.utc)
        difference_in_years = (
            today - self.date_created.replace(tzinfo=timezone.utc)
        ).days / 365
        difference = str(round(difference_in_years, 1)) + " år siden"
        if difference_in_years < 1:
            difference_in_months = round(
                (today - self.date_created.replace(tzinfo=timezone.utc)).days / 30
            )
            if difference_in_months == 1:
                difference = str(difference_in_months) + " måned siden"
            else:
                difference = str(difference_in_months) + " måneder siden"
            if difference_in_months < 1:
                difference_in_days = (
                    today - self.date_created.replace(tzinfo=timezone.utc)
                ).days
                if difference_in_days == 1:
                    difference = str(difference_in_days) + " dag siden"
                else:
                    difference = str(difference_in_days) + " dager siden"
                if difference_in_days < 1:
                    difference = "i dag"
        return difference

    def get_claimers(self):
        return (
            {int(claimer.user_id): claimer.user.first_name for claimer in self.claims}
            if self.claims
            else None
        )

    def get_co_wishers(self) -> dict | None:
        return (
            {
                int(co_wisher.co_wish_user_id): co_wisher.user.first_name
                for co_wisher in self.co_wishers
            }
            if self.co_wishers
            else None
        )

    def __repr__(self) -> str:
        return f"<Wish id={self.id} title={self.title!r}>"

    def tojson(self):
        if self.user_id == current_user.id:
            claimed = 0  # Eget ønske
        elif self.is_claimed_by_user(current_user.id):
            claimed = 1  # Andres ønsket, jeg har claimet
        elif self.claims:
            claimed = 2  # Andres ønske, andre har claimet
        else:
            claimed = 3  # Andres ønske, ingen har claimet

        date_now = datetime.now(timezone.utc)
        num_months = (
            date_now.year - self.date_created.replace(tzinfo=timezone.utc).year
        ) * 12 + (date_now.month - self.date_created.replace(tzinfo=timezone.utc).month)
        if not num_months:
            time_ago = str(date_now - self.date_created.replace(tzinfo=timezone.utc))
        else:
            time_ago = str(num_months)

        return {
            "id": self.id,
            "time_ago": time_ago,
            "user": "",
            "wish_title": self.title,
            "description": self.description,
            "url": self.url,
            "img_url": self.img_url,
            "claimed": claimed,
            "desired": self.desired,
        }


class WishInGroup(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    date_created: Mapped[datetime] = mapped_column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    wish_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("wish.id"), index=True)
    group_id: Mapped[int] = mapped_column(
        db.Integer, ForeignKey("group.id"), index=True
    )

    def __repr__(self) -> str:
        return f"<WishInGroup id={self.id} wish_id={self.wish_id}>"


class CoWishUser(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, ForeignKey("wish.id"), primary_key=True)
    date_created: Mapped[datetime] = mapped_column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    co_wish_user_id: Mapped[int] = mapped_column(
        db.Integer, ForeignKey("user.id"), primary_key=True
    )

    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<CoWishUser wish_id={self.id} co_wish_user_id={self.co_wish_user_id}>"


class GroupMember(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    date_created: Mapped[datetime] = mapped_column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"), index=True)
    group_id: Mapped[int] = mapped_column(
        db.Integer, ForeignKey("group.id"), index=True
    )

    def __repr__(self) -> str:
        return f"<GroupMember id={self.id} user_id={self.user_id} group_id={self.group_id}>"


class Group(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    date_created: Mapped[datetime] = mapped_column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    title: Mapped[str] = mapped_column(db.String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(db.String(255))

    def __repr__(self) -> str:
        return f"<Group id={self.id} title={self.title!r}>"
