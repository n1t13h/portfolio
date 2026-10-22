"""Request bodies shared by several routes."""

from pydantic import BaseModel

from app.schemas.base import CamelModel


class IdsBody(BaseModel):
    """A full, ordered list of ids (reordering)."""

    ids: list[str]


class PhotoIdsBody(CamelModel):
    photo_ids: list[str]
