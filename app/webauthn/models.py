from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

import pytz
from flask import current_app
from flask_login import current_user
from sqlalchemy import ForeignKey, desc
from sqlalchemy.dialects.mysql import BLOB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from user_agents import parse
from webauthn.helpers.structs import AuthenticatorTransport

from app import db
from app.auth.models import UserLogin
from app.constants import FULL_NORWEGIAN_MONTHS

if TYPE_CHECKING:
    from app.auth.models import User, UserLogin


class WebauthnCredential(db.Model):
    entry_id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    id: Mapped[bytes] = mapped_column(BLOB)
    public_key: Mapped[bytes] = mapped_column(BLOB)
    user_handle: Mapped[str] = mapped_column(db.String(64))
    rp_user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"))
    sign_count: Mapped[int] = mapped_column(db.Integer)
    transports: Mapped[Optional[List[AuthenticatorTransport]]] = mapped_column(db.String(255))
    label: Mapped[str] = mapped_column(db.String(90), default="Sikkerhetsnøkkel")
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=lambda: datetime.now(timezone.utc))

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
        current_app.logger.debug(f"Last used time type: {type(results)}")
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
        user_agent_string = db.session.scalar(db.select(UserLogin.user_agent)
                                              .where(UserLogin.credential == self.entry_id)
                                              .order_by(desc(UserLogin.login_time)))
        if user_agent_string is None:
            return None
        return parse(user_agent_string).os.family
