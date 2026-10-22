"""Admin photo models."""

from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, Field, ValidationInfo, field_validator

from app.models import Status
from app.schemas.base import CamelModel, storage_keys_to_urls


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
    # Rows hold storage keys (`variant_keys`); the context turns them into CDN URLs.
    variants: dict[str, str] = Field(validation_alias=AliasChoices("variants", "variant_keys"))
    created_at: datetime

    @field_validator("variants")
    @classmethod
    def _keys_to_urls(cls, keys: dict[str, str], info: ValidationInfo) -> dict[str, str]:
        return storage_keys_to_urls(keys, info)


class PhotoPatch(BaseModel):
    title: str | None = None
    place: str | None = None


class AllowDownloadBody(BaseModel):
    allow: bool
