from datetime import datetime
from flask_login import UserMixin, current_user
from sqlalchemy.orm import relationship

from app import db


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(90), nullable=False)
    email = db.Column(db.String(90))
    date_of_birth = db.Column(db.DateTime, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50))
    force_pw_change = db.Column(db.Integer, default=0)
    wishes = relationship("Wish", back_populates="user")

    def tojson(self):
        return {"id": self.id, "username": self.username}


class ClaimedWish(db.Model):
    wish_id = db.Column(db.Integer, db.ForeignKey("wish.id"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow())
    user = relationship("User")


class Wish(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    title = db.Column(db.String(90), nullable=False)
    description = db.Column(db.String(255))
    quantity = db.Column(db.Integer, nullable=False, default=1)
    url = db.Column(db.String(255))
    img_url = db.Column(db.String(255))
    desired = db.Column(db.Boolean, default=0)
    price = db.Column(db.Integer)
    user = relationship("User", back_populates="wishes")
    claimers = relationship("ClaimedWish")
    co_wishers = relationship("CoWishUser")

    # TODO: Viser "i dag", dagen etter. Bør stå "i dag" og "1 dag siden"
    def time_since_creation(self):
        today = datetime.utcnow()
        difference_in_years = (today - self.date_created).days / 365
        difference = str(difference_in_years) + " år siden"
        if difference_in_years < 1:
            difference_in_months = (today - self.date_created).days / 30
            difference = str(difference_in_months) + " måneder siden"
            if difference_in_months < 1:
                difference_in_days = (today - self.date_created).days
                difference = str(difference_in_days) + " dager siden"
                if difference_in_days < 1:
                    difference = "i dag"
        return difference

    def get_claimers(self):
        return {int(claimer.user_id): claimer.user.first_name for claimer in self.claimers} if self.claimers else None

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
    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    wish_id = db.Column(db.Integer, db.ForeignKey("wish.id"))
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"))


class CoWishUser(db.Model):
    id = db.Column(db.Integer, db.ForeignKey("wish.id"), primary_key=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    co_wish_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    user = relationship("User")

    def get_id(self):
        return self.id


class GroupMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"))


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    title = db.Column(db.String(30), nullable=False)
    description = db.Column(db.String(255))


class Suggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.Column(db.String(90), nullable=False)
