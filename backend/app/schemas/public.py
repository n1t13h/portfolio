"""Public response models. They carry no draft state, keys or internal ids."""

from pydantic import AliasChoices, Field, ValidationInfo, field_validator, model_validator

from app.schemas.base import CamelModel, storage_keys_to_urls


class PublicExif(CamelModel):
    camera: str | None = None
    focal_length: float | None = None
    aperture: float | None = None
    shutter: str | None = None
    iso: int | None = None


class PublicPhoto(CamelModel):
    id: str
    title: str
    place: str | None
    aspect_ratio: float
    exif: PublicExif
    variants: dict[str, str] = Field(validation_alias=AliasChoices("variants", "variant_keys"))
    allow_download: bool
    download_url: str | None = None  # a path on this API; only present when downloads are allowed

    @field_validator("variants")
    @classmethod
    def _keys_to_urls(cls, keys: dict[str, str], info: ValidationInfo) -> dict[str, str]:
        return storage_keys_to_urls(keys, info)

    @model_validator(mode="after")
    def _download_route(self) -> "PublicPhoto":
        self.download_url = f"/photos/{self.id}/download" if self.allow_download else None
        return self


class PublicChapter(CamelModel):
    title: str
    note: str
    photos: list[PublicPhoto]


class PublicCollectionSummary(CamelModel):
    slug: str
    title: str
    place: str
    year: str
    intro: str
    covers: list[PublicPhoto] = []  # chosen by the catalog service: only the visible ones


class PublicCollection(PublicCollectionSummary):
    chapters: list[PublicChapter]
    photos: list[PublicPhoto] = Field(description="every photo, in chapter order")
