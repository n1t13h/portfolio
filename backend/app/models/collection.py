"""A published essay: intro, cover photos and ordered chapters."""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import Status

if TYPE_CHECKING:
    from app.models.chapter import Chapter


class Collection(Base):
    __tablename__ = "collection"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    slug: Mapped[str] = mapped_column(String, unique=True)
    title: Mapped[str] = mapped_column(String)
    place: Mapped[str] = mapped_column(String, default="")
    year: Mapped[str] = mapped_column(String, default="")
    intro: Mapped[str] = mapped_column(String, default="")
    status: Mapped[Status] = mapped_column(Enum(Status, native_enum=False), default=Status.DRAFT)
    sort_position: Mapped[int] = mapped_column(default=0)
    cover_photo_ids: Mapped[list[str]] = mapped_column(JSON, default=list)

    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="collection",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Chapter.position",
    )
