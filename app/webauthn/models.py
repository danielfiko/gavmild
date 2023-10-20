from datetime import datetime
from typing import Optional, List
from sqlalchemy import ForeignKey, Column
# from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.database.database import db
from webauthn.helpers.structs import AuthenticatorTransport
from sqlalchemy.dialects.mysql import BLOB

class WebauthnCredential(db.Model):
    entry_id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    id: Mapped[bytes] = mapped_column(BLOB)
    public_key: Mapped[bytes] = mapped_column(BLOB)
    user_handle: Mapped[str] = mapped_column(db.String(64))
    rp_user_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("user.id"))
    sign_count: Mapped[int] = mapped_column(db.Integer)
    transports: Mapped[Optional[List[AuthenticatorTransport]]] = mapped_column(db.String(255))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="webauthn_credentials")
