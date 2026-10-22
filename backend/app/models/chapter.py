"""An ordered group of photos with a note, inside a collection."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.collection import Collection
    from app.models.photo import Photo


class Chapter(Base):
    __tablename__ = "chapter"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    collection_id: Mapped[str] = mapped_column(ForeignKey("collection.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String, default="")
    note: Mapped[str] = mapped_column(String, default="")
    position: Mapped[int] = mapped_column(default=0)

    collection: Mapped["Collection"] = relationship(back_populates="chapters")
    # The database sets photo.chapter_id to NULL on delete; photos are never deleted here.
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="chapter", passive_deletes=True, order_by="Photo.position_in_chapter"
    )
