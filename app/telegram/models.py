from datetime import datetime
from typing import Optional, List
from sqlalchemy import ForeignKey
#from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.database.database import db


class TelegramUser(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    tg_username: Mapped[Optional[str]] = mapped_column(db.String(90))
    user_id: Mapped[Optional[str]] = mapped_column(db.Integer, ForeignKey("user.id"), nullable=True)

    # Relationships
    suggestions: Mapped[List["Suggestion"]] = relationship(back_populates="tg_user")
    user: Mapped["User"] = relationship(back_populates="tg_user")


class Suggestion(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    date: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("telegram_user.id"))
    suggestion: Mapped[str] = mapped_column(db.String(255))
    solved_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    
    # Relationships
    tg_user: Mapped["TelegramUser"] = relationship(back_populates="suggestions")
