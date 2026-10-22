"""A message sent through the public contact form."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.photo import utcnow


class ContactMessage(Base):
    __tablename__ = "contact_message"

    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(String)
    ip: Mapped[str] = mapped_column(String, default="")
    notified: Mapped[bool] = mapped_column(default=False)
