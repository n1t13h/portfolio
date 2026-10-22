"""The single admin account."""

from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Admin(Base):
    __tablename__ = "admin"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(String)
    totp_secret: Mapped[str] = mapped_column(String)
    recovery_code_hashes: Mapped[list[Any]] = mapped_column(JSON, default=list)
    last_totp_step: Mapped[int | None]
    # Bumped on logout and credential reset; a session token carries the version it was issued at.
    session_version: Mapped[int] = mapped_column(default=0)
