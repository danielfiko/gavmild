from datetime import datetime
from typing import List
from sqlalchemy import ForeignKey
#from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.database.database import db
from flask_login import current_user


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
    date_created: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"))
    title: Mapped[str] = mapped_column(db.String(90), nullable=False)
    description: Mapped[str] = mapped_column(db.String(255))
    quantity: Mapped[int] = mapped_column(db.Integer, nullable=False, default=1)
    url: Mapped[str] = mapped_column(db.String(255))
    img_url: Mapped[str] = mapped_column(db.String(255))
    desired: Mapped[bool] = mapped_column(db.Boolean, default=0)
    price: Mapped[int] = mapped_column(db.Integer)
    
    # Relationships
    claims: Mapped[List["ClaimedWish"]] = relationship(back_populates="wish", cascade="delete")
    co_wishers: Mapped[List["CoWishUser"]] = relationship("CoWishUser", cascade="delete")

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


class WishInGroup(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    date_created: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
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
    description: Mapped[str] = mapped_column(db.String(255))