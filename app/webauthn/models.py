from datetime import datetime
from typing import Optional, List

import pytz
from flask_login import current_user
from sqlalchemy import ForeignKey, Column, desc
# from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import mapped_column, Mapped, relationship

from app.auth.models import UserLogin
from app.constants import FULL_NORWEGIAN_MONTHS
from app.database.database import db
from webauthn.helpers.structs import AuthenticatorTransport
from sqlalchemy.dialects.mysql import BLOB
from user_agents import parse


class WebauthnCredential(db.Model):
    entry_id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    id: Mapped[bytes] = mapped_column(BLOB)
    public_key: Mapped[bytes] = mapped_column(BLOB)
    user_handle: Mapped[str] = mapped_column(db.String(64))
    rp_user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"))
    sign_count: Mapped[int] = mapped_column(db.Integer)
    transports: Mapped[Optional[List[AuthenticatorTransport]]] = mapped_column(db.String(255))
    label: Mapped[str] = mapped_column(db.String(90), default="Sikkerhetsnøkkel")
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="webauthn_credentials")
    logins: Mapped["UserLogin"] = relationship(back_populates="webauthn_credentials")  # , cascade="all, delete")

    def current_user_is_owner(self):
        return current_user.id == self.rp_user_id

    def created_at_string(self):
        try:
            local_timestamp = self.created_at.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('Europe/Oslo'))
            month_number = local_timestamp.month
            month_name = FULL_NORWEGIAN_MONTHS[month_number]
            timestamp_string = local_timestamp.strftime('%H:%M %d. ' + month_name + ', %Y')
            return timestamp_string
        except AttributeError:
            return None

    def last_used_time(self):
        results = db.session.scalar(db.select(UserLogin.login_time)
                                    .where(UserLogin.credential == self.entry_id)
                                    .order_by(desc(UserLogin.login_time)))
        print(type(results))
        # return "ok"
        try:
            local_timestamp = results.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('Europe/Oslo'))
            month_number = local_timestamp.month
            month_name = FULL_NORWEGIAN_MONTHS[month_number]
            timestamp_string = local_timestamp.strftime('%H:%M %d. ' + month_name + ', %Y')
            return timestamp_string
        except AttributeError:
            return "-"

    def last_used_os(self):
        results = db.session.execute(db.select(UserLogin.user_agent)
                                     .where(UserLogin.credential == self.entry_id)
                                     .order_by(desc(UserLogin.login_time))).first()

        try:
            user_agent = parse(results.user_agent)
            operating_system = user_agent.os.family
            return operating_system
        except AttributeError:
            return None
