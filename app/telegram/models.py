from datetime import datetime
from typing import Optional, List
from sqlalchemy import ForeignKey
#from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.database.database import db


class TelegramUser(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    chat_username: Mapped[Optional[str]] = mapped_column(db.String(90))
    user_id: Mapped[Optional[int]] = mapped_column(db.Integer, ForeignKey("user.id"), nullable=True)

    # Relationships
    suggestions: Mapped[List["Suggestion"]] = relationship(back_populates="chat_user")
    user: Mapped["User"] = relationship(back_populates="chat_user")


class Suggestion(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    date: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("telegram_user.id"))
    suggestion: Mapped[str] = mapped_column(db.String(255))
    solved_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    
    # Relationships
    chat_user: Mapped["TelegramUser"] = relationship(back_populates="suggestions")


class TelegramUserConnection(db.Model):
    identifier: Mapped[str] = mapped_column(db.String(10), primary_key=True)
    user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"))


class ReportedLink(db.Model):
    wish_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("wish.id"), primary_key=True)
    reported_by_user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"), nullable=True)
    reported_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="reported_links")
    wish: Mapped["Wish"] = relationship(back_populates="reported_link")