from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from app import db
if TYPE_CHECKING:
    from app.auth.models import User
    from app.wishlist.models import Wish


class TelegramUser(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    chat_username: Mapped[Optional[str]] = mapped_column(db.String(90))
    user_id: Mapped[Optional[int]] = mapped_column(db.Integer, ForeignKey("user.id"), nullable=True)

    # Relationships
    suggestions: Mapped[List["Suggestion"]] = relationship(back_populates="chat_user")
    user: Mapped["User"] = relationship(back_populates="chat_user")

    @classmethod
    def create(cls, id: int, chat_username: Optional[str] = None, user_id: Optional[int] = None) -> "TelegramUser":
        telegram_user = cls()
        telegram_user.id = id
        telegram_user.chat_username = chat_username
        telegram_user.user_id = user_id
        db.session.add(telegram_user)
        return telegram_user


class Suggestion(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    date: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.now(timezone.utc))
    user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("telegram_user.id"))
    suggestion: Mapped[str] = mapped_column(db.String(255))
    solved_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    
    # Relationships 
    chat_user: Mapped["TelegramUser"] = relationship(back_populates="suggestions")

    @classmethod
    def create(cls, user_id: int, suggestion: str) -> "Suggestion":
        new_suggestion = cls()
        new_suggestion.user_id = user_id
        new_suggestion.suggestion = suggestion
        db.session.add(new_suggestion)
        return new_suggestion


class TelegramUserConnection(db.Model):
    identifier: Mapped[str] = mapped_column(db.String(10), primary_key=True)
    user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"))
    
    @classmethod
    def create(cls, user_id: int, identifier: str) -> "TelegramUserConnection":
        new_connection = cls()
        new_connection.user_id = user_id
        new_connection.identifier = identifier
        db.session.add(new_connection)
        return new_connection

class ReportedLink(db.Model):
    wish_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("wish.id"), primary_key=True)
    reported_by_user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"), nullable=True)
    reported_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.now(timezone.utc))
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="reported_links")
    wish: Mapped["Wish"] = relationship(back_populates="reported_link")