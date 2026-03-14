from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, List, Optional

from flask import current_app
from flask_login import UserMixin
from sqlalchemy import ForeignKey, desc, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from user_agents import parse

from app import db, login_manager
from app.constants import ABBREVIATED_NORWEGIAN_MONTHS

if TYPE_CHECKING:
    from app.telegram.models import ReportedLink, TelegramUser
    from app.webauthn.models import WebauthnCredential
    from app.wishlist.models import ClaimedWish, Wish
    

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class User(db.Model, UserMixin):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    date_created: Mapped[datetime] = mapped_column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    username: Mapped[str] = mapped_column(db.String(20), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(db.String(90), nullable=False)
    email: Mapped[str] = mapped_column(db.String(90), unique=True)
    date_of_birth: Mapped[datetime] = mapped_column(db.DateTime, nullable=False)
    first_name: Mapped[str] = mapped_column(db.String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(db.String(50))
    force_pw_change: Mapped[int] = mapped_column(db.Integer, default=0)

    # Relationships
    wishes: Mapped[List["Wish"]] = relationship(back_populates="user")
    claimed_wishes: Mapped[List["ClaimedWish"]] = relationship(back_populates="user")
    chat_user: Mapped["TelegramUser"] = relationship(back_populates="user")
    reported_links: Mapped[List["ReportedLink"]] = relationship(back_populates="user")
    preferences: Mapped["UserPreferences"] = relationship(back_populates="user")
    password_reset_tokens: Mapped[List["PasswordResetToken"]] = relationship(back_populates="user")
    # lists: Mapped[List["WishList"]] = relationship(back_populates="user")
    webauthn_credentials: Mapped[List["WebauthnCredential"]] = relationship(back_populates="user")
    logins: Mapped[List["UserLogin"]] = relationship(back_populates="user")

    def tojson(self):
        return {"id": self.id, "username": self.username}

    def get_first_name(self):
        return self.first_name

    @classmethod
    def create(cls, first_name: str, last_name: str, email: str, hashed_password: str, date_of_birth: datetime, username: str) -> "User":
        user = cls()
        user.first_name = first_name.title()
        user.last_name = last_name.title()
        user.email = email.casefold()
        user.password = hashed_password
        user.date_of_birth = date_of_birth
        user.username = username
        return user
    
    @staticmethod
    def upcoming_birthdays():
        # Get users with birthday next 60 days
        month_mappings = ABBREVIATED_NORWEGIAN_MONTHS
        start = datetime.now()
        end = start + timedelta(days=60)
        turn_of_year_days = 0
        if start.year != end.year:
            turn_of_year_days = 365

        user_birthdays = db.session.execute(
            db.select(User)
            .where(func.dayofyear(User.date_of_birth) >= func.dayofyear(start))
            .where(func.dayofyear(User.date_of_birth) <= func.dayofyear(end) + turn_of_year_days)
            .order_by(func.dayofyear(User.date_of_birth))
        ).all()

        if len(user_birthdays) == 0:
            current_app.logger.debug("No upcoming birthdays found in the next 60 days. Finding the next closest birthday.")
            user = db.session.execute(
                db.select(User)
                .where(func.dayofyear(User.date_of_birth) >= func.dayofyear(start))
                .order_by(func.dayofyear(User.date_of_birth))
            ).first()

            if user is None:
                current_app.logger.debug("No birthdays found later this year. Finding the first birthday next year.")
                user = db.session.execute(
                    db.select(User)
                    .order_by(func.dayofyear(User.date_of_birth))
                ).first()

            if user is None:
                return []
            
            birthdays = [{"id": user.id, "first_name": user.first_name,
                          "birthday": f"{user.date_of_birth.day}. {month_mappings[user.date_of_birth.month]}"}]
        else:
            birthdays = [{"id": u[0].id, "first_name": u[0].first_name,
                          "birthday": f"{u[0].date_of_birth.day}. {month_mappings[u[0].date_of_birth.month]}"} for u in
                         user_birthdays]

        current_app.logger.debug(f"Upcoming birthdays fetched: {len(birthdays)}")
        return birthdays

    def last_login(self):
        result = db.session.execute(db.select(UserLogin.user_agent, UserLogin.login_time)
                                    .where(UserLogin.user_id == self.id)
                                    .order_by(desc(UserLogin.login_time))).first()
        if result is None:
            return None, None
        
        user_agent = parse(result.user_agent)
        operating_system = user_agent.os.family
        return result.login_time, operating_system

class UserPreferences(db.Model):
    user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"), primary_key=True)
    order_users_by: Mapped[Optional[str]] = mapped_column(db.String(20))
    show_claims: Mapped[int] = mapped_column(db.Integer, default=1)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="preferences")

    @classmethod
    def create(cls, user_id: int, order_users_by: str | None = None, show_claims: int = 1) -> "UserPreferences":
        prefs = cls()
        prefs.user_id = user_id
        prefs.order_users_by = order_users_by
        prefs.show_claims = show_claims
        return prefs


class PasswordResetToken(db.Model):
    token_id: Mapped[str] = mapped_column(db.String(10), primary_key=True)
    token: Mapped[str] = mapped_column(db.String(90))
    user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(db.DateTime)
    used_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="password_reset_tokens")

    @classmethod
    def create(cls, token_id: str, token: str, user_id: int, expires_at: datetime) -> "PasswordResetToken":
        entry = cls()
        entry.token_id = token_id
        entry.token = token
        entry.user_id = user_id
        entry.expires_at = expires_at
        return entry


class UserLogin(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"))
    login_type: Mapped[str] = mapped_column(db.String(90))
    login_time: Mapped[datetime] = mapped_column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ip_address: Mapped[str] = mapped_column(db.String(39))
    user_agent: Mapped[str] = mapped_column(db.String(255))
    credential: Mapped[Optional[int]] = mapped_column(
        db.Integer,
        ForeignKey("webauthn_credential.entry_id"))  # , ondelete="SET NULL"))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="logins")
    webauthn_credentials: Mapped[List["WebauthnCredential"]] = relationship(
        back_populates="logins")

    @classmethod
    def create(cls, user_id: int, login_type: str, ip_address: str, user_agent: str, credential: int | None = None) -> "UserLogin":
        entry = cls()
        entry.user_id = user_id
        entry.login_type = login_type
        entry.ip_address = ip_address
        entry.user_agent = user_agent
        entry.credential = credential
        return entry
