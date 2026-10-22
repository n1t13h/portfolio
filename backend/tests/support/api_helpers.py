"""Small builders that drive the admin API the way the admin UI would."""

from typing import Any

from fastapi.testclient import TestClient

from app.integrations.storage import Bucket
from tests.fakes import FakeStorage
from tests.support.images import make_jpeg


def upload(c: TestClient, storage: FakeStorage, base: str, data: bytes) -> str:
    """Runs the browser's side of the flow: ask for a URL, PUT the bytes, return the id."""
    ticket = c.post(f"{base}/upload-url").json()
    storage.put_bytes(Bucket.PRIVATE, ticket["key"], data, "image/jpeg")
    return str(ticket["photoId"])


def add_photo(
    c: TestClient,
    storage: FakeStorage,
    admin_url: str,
    size: tuple[int, int] = (1200, 800),
    data: bytes | None = None,
) -> dict[str, Any]:
    base = f"{admin_url}/photos"
    photo_id = upload(c, storage, base, data or make_jpeg(size))
    resp = c.post(f"{base}/{photo_id}/confirm")
    assert resp.status_code == 200, resp.text
    result: dict[str, Any] = resp.json()
    return result


def add_collection(c: TestClient, admin_url: str, slug: str, **fields: str) -> dict[str, Any]:
    resp = c.post(f"{admin_url}/collections", json={"slug": slug, "title": slug.title(), **fields})
    assert resp.status_code == 201, resp.text
    result: dict[str, Any] = resp.json()
    return result


def add_chapter(c: TestClient, admin_url: str, collection_id: str, **fields: str) -> dict[str, Any]:
    resp = c.post(f"{admin_url}/collections/{collection_id}/chapters", json=fields)
    assert resp.status_code == 201, resp.text
    result: dict[str, Any] = resp.json()
    return result


def add_published_photo(
    c: TestClient, storage: FakeStorage, admin_url: str, title: str = "", **kwargs: Any
) -> dict[str, Any]:
    photo = add_photo(c, storage, admin_url, **kwargs)
    c.patch(f"{admin_url}/photos/{photo['id']}", json={"title": title})
    resp = c.post(f"{admin_url}/photos/{photo['id']}/publish")
    result: dict[str, Any] = resp.json()
    return result


def put_in_chapter(c: TestClient, admin_url: str, chapter_id: str, photo_ids: list[str]) -> None:
    resp = c.post(f"{admin_url}/chapters/{chapter_id}/photos", json={"photoIds": photo_ids})
    assert resp.status_code == 200, resp.text
