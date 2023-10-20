from app.database.database import db
from datetime import datetime
from typing import List, Optional
from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship
from flask_login import UserMixin


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
    #lists: Mapped[List["WishList"]] = relationship(back_populates="user")
    webauthn_credentials: Mapped[List["WebauthnCredential"]] = relationship(back_populates="user")


    def tojson(self):
        return {"id": self.id, "username": self.username}


    def get_first_name(self):
        return self.first_name


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

    #Relationships
    user: Mapped["User"] = relationship(back_populates="password_reset_tokens")
