from datetime import datetime, timezone
from typing import TYPE_CHECKING, List

from flask_login import current_user
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db

if TYPE_CHECKING:
    from app.auth.models import User
    from app.telegram.models import ReportedLink

# wishes_in_list = db.Table(
#     "wishes_in_list",
#     Column("wish", ForeignKey("wish.id"), primary_key=True),
#     Column("list", ForeignKey("wish_list.id"), primary_key=True),
# )


# TODO: Make date_created timezone-aware at the database level
#  1. Change the column to DateTime(timezone=True) (SQLAlchemy) or use auto_now_add=True (Django)
#  2. Write a migration to backfill existing rows: UPDATE table SET date_created = date_created AT TIME ZONE 'UTC'
#  3. Remove the .replace(tzinfo=timezone.utc) workaround once migration is applied


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
    desired: Mapped[bool] = mapped_column(db.Boolean, default=0)
    price: Mapped[int | None] = mapped_column(db.Integer)
    # State tracking: both NULL = active; archived_at set = archived; deleted_at set = soft-deleted
    archived_at: Mapped[datetime | None] = mapped_column(db.DateTime)
    deleted_at: Mapped[datetime | None] = mapped_column(db.DateTime)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="wishes")
    claims: Mapped[List["ClaimedWish"]] = relationship(
        back_populates="wish", cascade="all, delete-orphan"
    )
    co_wishers: Mapped[List["CoWishUser"]] = relationship(
        "CoWishUser", cascade="delete"
    )
    reported_link: Mapped["ReportedLink"] = relationship(back_populates="wish")
    # lists: Mapped[List["WishList"]] = relationship(
    #     secondary=wishes_in_list, back_populates="wishes"
    # )

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


# TODO: Remove all commented-out WishList code below — either implement it or clean it up to reduce noise.
# class WishList(db.Model):
#     id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
#     user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"))
#     title: Mapped[str] = mapped_column(db.String(30))
#     default_list: Mapped[int] = mapped_column(db.Integer, default=0)
#     private: Mapped[int] = mapped_column(db.Integer, default=0)
#     created_at: Mapped[datetime] = mapped_column(db.DateTime, default=func.utcnow())
#     expires_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
#     archived_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
#
#     # Relationship
#     wishes: Mapped[List[Wish]] = relationship(
#         secondary=wishes_in_list, back_populates="lists"
#     )
#     user: Mapped["User"] = relationship(back_populates="lists")
#
#     def is_active(self):
#         print(f"Title: {self.title}")
#         now = datetime.now(timezone.utc)
#         return self.expires_at > now and self.archived_at > now if self.archived_at is not None else True
#
#     @staticmethod
#     def get_active_lists_from_ids(list_ids):
#         return db.session.execute(
#             db.select(WishList)
#             .where(
#                 WishList.id.in_(list_ids),
#                 WishList.user_id == current_user.id,
#                 WishList.expires_at > datetime.now(timezone.utc),
#                 WishList.archived_at.is_(None))
#         ).scalars()
#
#     @staticmethod
#     def get_active_list_ids(list_ids):
#         active_lists = WishList.get_active_lists_from_ids(list_ids)
#         active_ids = []
#         for wish_list in active_lists:
#             active_ids.append(wish_list.id)
#         return active_ids
#
#     @staticmethod
#     def get_active_lists(user_id):
#         query = (db.select(WishList.id, WishList.title, WishList.expires_at, WishList.private)
#                  .where(
#                     WishList.user_id == user_id,
#                     WishList.default_list  == 0,
#                     WishList.expires_at > datetime.now(timezone.utc),
#                     WishList.archived_at.is_(None)
#                 ))
#
#         if not user_id == current_user.id:
#             query = query.where(not WishList.private)
#
#         result = db.session.execute(query).mappings().all()
#         return result
