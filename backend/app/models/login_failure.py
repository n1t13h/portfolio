"""One failed login attempt, used to lock out repeated guessing."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class LoginFailure(Base):
    __tablename__ = "login_failure"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String, index=True)  # "<ip>|<username>"
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
