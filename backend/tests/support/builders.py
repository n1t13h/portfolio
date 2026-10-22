"""Small builders for entities used in repository and service tests."""

from datetime import UTC, datetime, timedelta
from typing import Any

from app.models import Chapter, Collection, Photo, Status


def make_photo(photo_id: str, **overrides: Any) -> Photo:
    values: dict[str, Any] = {"title": photo_id, "aspect_ratio": 1.5}
    values.update(overrides)
    return Photo(id=photo_id, **values)


def make_collection(collection_id: str, **overrides: Any) -> Collection:
    values: dict[str, Any] = {"slug": collection_id, "title": collection_id, "sort_position": 0}
    values.update(overrides)
    return Collection(id=collection_id, **values)


def make_chapter(chapter_id: str, collection_id: str, **overrides: Any) -> Chapter:
    values: dict[str, Any] = {"title": chapter_id, "position": 0}
    values.update(overrides)
    return Chapter(id=chapter_id, collection_id=collection_id, **values)


def published(**overrides: Any) -> dict[str, Any]:
    return {"status": Status.PUBLISHED, **overrides}


def at(minutes: int = 0) -> datetime:
    """A fixed UTC moment, `minutes` after noon on 2026-01-01."""
    return datetime(2026, 1, 1, 12, tzinfo=UTC) + timedelta(minutes=minutes)
