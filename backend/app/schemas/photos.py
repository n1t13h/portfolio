"""Admin photo models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models import Status
from app.schemas.base import CamelModel


class UploadTicketOut(CamelModel):
    photo_id: str
    put_url: str
    key: str


class PhotoOut(CamelModel):
    id: str
    title: str
    place: str | None
    aspect_ratio: float
    exif: dict[str, Any]
    taken_at: datetime | None
    status: Status
    allow_download: bool
    sort_position: int
    chapter_id: str | None
    unsplash_id: str | None
    variants: dict[str, str]  # long edge -> public CDN URL
    created_at: datetime


class PhotoPatch(BaseModel):
    title: str | None = None
    place: str | None = None


class AllowDownloadBody(BaseModel):
    allow: bool
