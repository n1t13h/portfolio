"""A single photograph and where its files live in R2."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import Status

if TYPE_CHECKING:
    from app.models.chapter import Chapter


def utcnow() -> datetime:
    return datetime.now(UTC)


class Photo(Base):
    __tablename__ = "photo"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, default="")
    place: Mapped[str | None] = mapped_column(String)
    aspect_ratio: Mapped[float]
    exif: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[Status] = mapped_column(Enum(Status, native_enum=False), default=Status.DRAFT)
    allow_download: Mapped[bool] = mapped_column(default=False)
    sort_position: Mapped[int] = mapped_column(default=0)
    chapter_id: Mapped[str | None] = mapped_column(ForeignKey("chapter.id", ondelete="SET NULL"))
    position_in_chapter: Mapped[int] = mapped_column(default=0)
    unsplash_id: Mapped[str | None] = mapped_column(String, unique=True)
    unsplash_url: Mapped[str | None] = mapped_column(String)
    original_key: Mapped[str | None] = mapped_column(String)
    variant_keys: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    download_key: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    chapter: Mapped["Chapter | None"] = relationship(back_populates="photos")
