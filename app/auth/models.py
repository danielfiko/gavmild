from app.constants import ABBREVIATED_NORWEGIAN_MONTHS
from app.database.database import db
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import ForeignKey, func, desc
from sqlalchemy.orm import mapped_column, Mapped, relationship
from flask_login import UserMixin, current_user
from user_agents import parse


class User(db.Model, UserMixin):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    date_created: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    username: Mapped[str] = mapped_column(db.String(20), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(db.String(90), nullable=False)
    email: Mapped[str] = mapped_column(db.String(90))
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
    logins: Mapped["UserLogin"] = relationship(back_populates="user")

    def tojson(self):
        return {"id": self.id, "username": self.username}

    def get_first_name(self):
        return self.first_name

    @staticmethod
    def upcoming_birthdays():
        # Get users with birthday next 60 days
        month_mappings = ABBREVIATED_NORWEGIAN_MONTHS
        start = datetime.now()
        end = start + timedelta(days=60)
        user_birthdays = db.session.execute(
            db.select(User)
            .where(func.dayofyear(User.date_of_birth) >= func.dayofyear(start))
            .where(func.dayofyear(User.date_of_birth) <= func.dayofyear(end))
            .order_by(func.dayofyear(User.date_of_birth))
        ).scalars()
        birthdays = [{"id": u.id, "first_name": u.first_name,
                      "birthday": f"{u.date_of_birth.day}. {month_mappings[u.date_of_birth.month]}"} for u in
                     user_birthdays]
        return birthdays

    def last_login(self):
        result = db.session.execute(db.select(UserLogin.user_agent, UserLogin.login_time)
                                    .where(UserLogin.user_id == self.id)
                                    .order_by(desc(UserLogin.login_time))).first()
        print(result)
        try:
            user_agent = parse(result.user_agent)
            operating_system = user_agent.os.family
            return result.login_time, operating_system
        except AttributeError:
            return None, None


class UserPreferences(db.Model):
    user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"), primary_key=True)
    order_users_by: Mapped[Optional[str]] = mapped_column(db.String(20))
    show_claims: Mapped[int] = mapped_column(db.Integer, default=1)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="preferences")


class PasswordResetToken(db.Model):
    token_id: Mapped[str] = mapped_column(db.String(10), primary_key=True)
    token: Mapped[str] = mapped_column(db.String(90))
    user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(db.DateTime)
    used_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="password_reset_tokens")


class UserLogin(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"))
    login_type: Mapped[str] = mapped_column(db.String(90))
    login_time: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    ip_address: Mapped[str] = mapped_column(db.String(39))
    user_agent: Mapped[str] = mapped_column(db.String(255))
    credential: Mapped[Optional[int]] = mapped_column(db.Integer, ForeignKey("webauthn_credential.entry_id"))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="logins")
