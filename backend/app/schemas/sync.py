"""Unsplash sync models."""

from datetime import datetime

from app.schemas.base import CamelModel


class SyncStatusOut(CamelModel):
    running: bool
    last_started_at: datetime | None
    last_finished_at: datetime | None
    last_imported: int
    last_error: str | None
    rate_limit_remaining: int | None
    pending: int
