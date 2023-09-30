from app.database.database import db
from datetime import datetime
from typing import List
from flask_sqlalchemy import SQLAlchemy
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
    wishes: Mapped[List["Wish"]] = relationship(backref="user")
    claimed_wishes: Mapped[List["ClaimedWish"]] = relationship(back_populates="user")
    tg_user: Mapped["TelegramUser"] = relationship(back_populates="user")


    def tojson(self):
        return {"id": self.id, "username": self.username}


    def get_first_name(self):
        return self.first_name
