from app.database.database import db
from datetime import datetime
from typing import List, Optional
from sqlalchemy import ForeignKey, Column, func
#from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import mapped_column, Mapped, relationship
from flask_login import current_user


# wishes_in_list = db.Table(
#     "wishes_in_list",
#     Column("wish", ForeignKey("wish.id"), primary_key=True),
#     Column("list", ForeignKey("wish_list.id"), primary_key=True),
# )


class ClaimedWish(db.Model):
    wish_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("wish.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"), primary_key=True)
    quantity: Mapped[int] = mapped_column(db.Integer, nullable=False)
    date: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="claimed_wishes")
    wish: Mapped["Wish"] = relationship(back_populates="claims")


class Wish(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    date_created: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow())
    user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"))
    title: Mapped[str] = mapped_column(db.String(90), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(db.String(255))
    quantity: Mapped[int] = mapped_column(db.Integer, nullable=False, default=1)
    url: Mapped[Optional[str]] = mapped_column(db.String(255))
    img_url: Mapped[Optional[str]] = mapped_column(db.String(255))
    desired: Mapped[bool] = mapped_column(db.Boolean, default=0)
    price: Mapped[Optional[int]] = mapped_column(db.Integer)
    
    # Relationships
    user: Mapped[List["User"]] = relationship(back_populates="wishes")
    claims: Mapped[List["ClaimedWish"]] = relationship(back_populates="wish", cascade="delete")
    co_wishers: Mapped[List["CoWishUser"]] = relationship("CoWishUser", cascade="delete")
    reported_link: Mapped["ReportedLink"] = relationship(back_populates="wish")
    # lists: Mapped[List["WishList"]] = relationship(
    #     secondary=wishes_in_list, back_populates="wishes"
    # )


    def is_claimed_by_user(self, user_id):
        """Check if the wish is claimed by the specified user."""
        return any(claim.user.id == user_id for claim in self.claims)
    
    # TODO: Viser "i dag", dagen etter. Bør stå "i dag" og "1 dag siden"
    def time_since_creation(self):
        today = datetime.utcnow()
        difference_in_years = (today - self.date_created).days / 365
        difference = str(round(difference_in_years, 1)) + " år siden"
        if difference_in_years < 1:
            difference_in_months = round((today - self.date_created).days / 30)
            if difference_in_months == 1:
                difference = str(difference_in_months) + " måned siden"
            else:
                difference = str(difference_in_months) + " måneder siden"
            if difference_in_months < 1:
                difference_in_days = (today - self.date_created).days
                if difference_in_days == 1:
                    difference = str(difference_in_days) + " dag siden"
                else:
                    difference = str(difference_in_days) + " dager siden"
                if difference_in_days < 1:
                    difference = "i dag"
        return difference

    def get_claimers(self):
        return {int(claimer.user_id): claimer.user.first_name for claimer in self.claims} if self.claims else None

    def get_co_wishers(self):
        return {int(co_wisher.co_wish_user_id): co_wisher.user.first_name for co_wisher in self.co_wishers} if self.co_wishers else None

    def co_wisher(self):
        return db.session.query(User.first_name, User.id).join(CoWishUser).filter(CoWishUser.id == self.id).all()

    def user_name(self):
        return db.session.query(User.first_name).filter(User.id == self.user_id).one()

    def tojson(self):
        if self.user_id == current_user.id:
            claimed = 0  # Eget ønske
        elif self.claimed_by_user_id == current_user.id:
            claimed = 1  # Andres ønsket, jeg har claimet
        elif self.claimed_by_user_id:
            claimed = 2  # Andres ønske, andre har claimet
        else:
            claimed = 3  # Andres ønske, ingen har claimet

        date_now = datetime.utcnow()
        num_months = (date_now.year - self.date_created.year) * 12 + (date_now.month - self.date_created.month)
        if not num_months:
            time_ago = str(date_now - self.date_created)
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
            "desired": self.desired
        }

    # def __repr__(self):
    #    return "<Task %r>" % self.id


class ArchivedWish(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    date_created: Mapped[datetime] = mapped_column(db.DateTime)
    user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"))
    title: Mapped[str] = mapped_column(db.String(90), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(db.String(255))
    quantity: Mapped[int] = mapped_column(db.Integer, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(db.String(255))
    img_url: Mapped[Optional[str]] = mapped_column(db.String(255))
    desired: Mapped[bool] = mapped_column(db.Boolean, default=0)
    price: Mapped[Optional[int]] = mapped_column(db.Integer)
    deleted_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow())


class WishInGroup(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    date_created: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow())
    wish_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("wish.id"))
    group_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("group.id"))


class CoWishUser(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, ForeignKey("wish.id"), primary_key=True)
    date_created: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    co_wish_user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"), primary_key=True)
    
    user: Mapped["User"] = relationship("User")

    def get_id(self):
        return self.id


class GroupMember(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    date_created: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"))
    group_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("group.id"))


class Group(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    date_created: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    title: Mapped[str] = mapped_column(db.String(30), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(db.String(255))


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
#         now = datetime.utcnow()
#         return self.expires_at > now and self.archived_at > now if self.archived_at is not None else True
#
#     @staticmethod
#     def get_active_lists_from_ids(list_ids):
#         return db.session.execute(
#             db.select(WishList)
#             .where(
#                 WishList.id.in_(list_ids),
#                 WishList.user_id == current_user.id,
#                 WishList.expires_at > datetime.utcnow(),
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
#                     WishList.expires_at > datetime.utcnow(),
#                     WishList.archived_at.is_(None)
#                 ))
#
#         if not user_id == current_user.id:
#             query = query.where(not WishList.private)
#
#         result = db.session.execute(query).mappings().all()
#         return result