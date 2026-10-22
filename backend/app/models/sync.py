"""Single-row state for the Unsplash sync: last result and the run lock."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SyncState(Base):
    __tablename__ = "sync_state"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    running: Mapped[bool] = mapped_column(default=False)
    last_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_imported: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(String)
    rate_limit_remaining: Mapped[int | None]
    # Unsplash ids found but not yet imported, with how many times each has failed.
    pending: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    # Ids the sync must never import: "failed" (given up) or "deleted" (removed by the admin).
    skipped: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
