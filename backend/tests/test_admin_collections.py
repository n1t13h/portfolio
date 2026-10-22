from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog
from tests.api_helpers import add_chapter, add_collection, add_photo
from tests.fakes import FakeStorage


def get_collection(c: TestClient, url: str, collection_id: str) -> dict[str, Any]:
    result: dict[str, Any] = c.get(f"{url}/collections/{collection_id}").json()
    return result


def chapter_photo_ids(c: TestClient, url: str, collection_id: str, chapter_id: str) -> list[str]:
    chapters = get_collection(c, url, collection_id)["chapters"]
    ids: list[str] = next(ch["photoIds"] for ch in chapters if ch["id"] == chapter_id)
    return ids


def assign(c: TestClient, url: str, chapter_id: str, photo_ids: list[str]) -> Any:
    return c.post(f"{url}/chapters/{chapter_id}/photos", json={"photoIds": photo_ids})


def test_new_collection_is_a_draft_appended_to_the_order(
    admin_client: TestClient, admin_url: str
) -> None:
    first = add_collection(admin_client, admin_url, "one")
    second = add_collection(admin_client, admin_url, "two")
    assert first["status"] == "draft"
    ids = [c["id"] for c in admin_client.get(f"{admin_url}/collections").json()]
    assert ids == [first["id"], second["id"]]


def test_collection_order_is_admin_controlled(admin_client: TestClient, admin_url: str) -> None:
    ids = [add_collection(admin_client, admin_url, s)["id"] for s in ("a", "b", "c")]
    resp = admin_client.put(f"{admin_url}/collections/order", json={"ids": ids[::-1]})
    assert resp.status_code == 204
    listed = [c["id"] for c in admin_client.get(f"{admin_url}/collections").json()]
    assert listed == ids[::-1]


def test_duplicate_slug_rejected(admin_client: TestClient, admin_url: str) -> None:
    add_collection(admin_client, admin_url, "goa")
    resp = admin_client.post(f"{admin_url}/collections", json={"slug": "goa", "title": "Again"})
    assert resp.status_code == 409


@pytest.mark.parametrize("slug", ["Has Caps", "has space", "-lead", "trail-", "a/b", ""])
def test_invalid_slug_rejected(admin_client: TestClient, admin_url: str, slug: str) -> None:
    resp = admin_client.post(f"{admin_url}/collections", json={"slug": slug, "title": "T"})
    assert resp.status_code == 422


def test_update_collection_and_chapter(admin_client: TestClient, admin_url: str) -> None:
    col = add_collection(admin_client, admin_url, "goa")
    chapter = add_chapter(admin_client, admin_url, col["id"], title="Arrival")
    resp = admin_client.patch(
        f"{admin_url}/collections/{col['id']}",
        json={"title": "Goa", "place": "India", "year": "2024", "intro": "Hello"},
    )
    assert (resp.json()["title"], resp.json()["year"]) == ("Goa", "2024")
    resp = admin_client.patch(f"{admin_url}/chapters/{chapter['id']}", json={"note": "Monsoon"})
    assert (resp.json()["title"], resp.json()["note"]) == ("Arrival", "Monsoon")


def test_publish_and_unpublish_collection(admin_client: TestClient, admin_url: str) -> None:
    col = add_collection(admin_client, admin_url, "goa")
    url = f"{admin_url}/collections/{col['id']}"
    assert admin_client.post(f"{url}/publish").json()["status"] == "published"
    assert admin_client.post(f"{url}/unpublish").json()["status"] == "draft"


def test_assigning_photo_to_second_chapter_moves_it(
    admin_client: TestClient, admin_url: str, storage: FakeStorage
) -> None:
    col = add_collection(admin_client, admin_url, "goa")
    a = add_chapter(admin_client, admin_url, col["id"], title="A")
    b = add_chapter(admin_client, admin_url, col["id"], title="B")
    photo = add_photo(admin_client, storage, admin_url)
    assert assign(admin_client, admin_url, a["id"], [photo["id"]]).status_code == 200
    assert assign(admin_client, admin_url, b["id"], [photo["id"]]).status_code == 200
    assert chapter_photo_ids(admin_client, admin_url, col["id"], a["id"]) == []
    assert chapter_photo_ids(admin_client, admin_url, col["id"], b["id"]) == [photo["id"]]


def test_photo_can_move_between_collections(
    admin_client: TestClient, admin_url: str, storage: FakeStorage
) -> None:
    c1 = add_collection(admin_client, admin_url, "one")
    c2 = add_collection(admin_client, admin_url, "two")
    ch1 = add_chapter(admin_client, admin_url, c1["id"])
    ch2 = add_chapter(admin_client, admin_url, c2["id"])
    photo = add_photo(admin_client, storage, admin_url)
    assign(admin_client, admin_url, ch1["id"], [photo["id"]])
    assign(admin_client, admin_url, ch2["id"], [photo["id"]])
    assert chapter_photo_ids(admin_client, admin_url, c1["id"], ch1["id"]) == []
    assert chapter_photo_ids(admin_client, admin_url, c2["id"], ch2["id"]) == [photo["id"]]


def test_assign_appends_in_given_order_and_keeps_existing(
    admin_client: TestClient, admin_url: str, storage: FakeStorage
) -> None:
    col = add_collection(admin_client, admin_url, "goa")
    ch = add_chapter(admin_client, admin_url, col["id"])
    p1, p2, p3 = (add_photo(admin_client, storage, admin_url)["id"] for _ in range(3))
    assign(admin_client, admin_url, ch["id"], [p1])
    assign(admin_client, admin_url, ch["id"], [p3, p2])
    assert chapter_photo_ids(admin_client, admin_url, col["id"], ch["id"]) == [p1, p3, p2]


def test_assign_with_unknown_or_duplicate_photo_is_rejected_atomically(
    admin_client: TestClient, admin_url: str, storage: FakeStorage
) -> None:
    col = add_collection(admin_client, admin_url, "goa")
    ch = add_chapter(admin_client, admin_url, col["id"])
    real = add_photo(admin_client, storage, admin_url)["id"]
    assert assign(admin_client, admin_url, ch["id"], [real, "f" * 32]).status_code == 422
    assert assign(admin_client, admin_url, ch["id"], [real, real]).status_code == 422
    assert chapter_photo_ids(admin_client, admin_url, col["id"], ch["id"]) == []


def test_remove_photo_from_chapter(
    admin_client: TestClient, admin_url: str, storage: FakeStorage
) -> None:
    col = add_collection(admin_client, admin_url, "goa")
    ch = add_chapter(admin_client, admin_url, col["id"])
    photo = add_photo(admin_client, storage, admin_url)["id"]
    assign(admin_client, admin_url, ch["id"], [photo])
    assert admin_client.delete(f"{admin_url}/chapters/{ch['id']}/photos/{photo}").status_code == 204
    assert chapter_photo_ids(admin_client, admin_url, col["id"], ch["id"]) == []
    # removing again: it is no longer in that chapter
    assert admin_client.delete(f"{admin_url}/chapters/{ch['id']}/photos/{photo}").status_code == 404


def build_for_reorder(
    c: TestClient, url: str, storage: FakeStorage, level: str
) -> tuple[str, list[str]]:
    """Returns (reorder url, current ids) for collections, chapters or a chapter's photos."""
    if level == "collections":
        ids = [add_collection(c, url, s)["id"] for s in ("a", "b", "c")]
        return f"{url}/collections/order", ids
    col = add_collection(c, url, "goa")
    if level == "chapters":
        ids = [add_chapter(c, url, col["id"], title=t)["id"] for t in "abc"]
        return f"{url}/collections/{col['id']}/chapters/order", ids
    ch = add_chapter(c, url, col["id"])
    ids = [add_photo(c, storage, url)["id"] for _ in range(3)]
    assign(c, url, ch["id"], ids)
    return f"{url}/chapters/{ch['id']}/photos/order", ids


def current_ids(c: TestClient, url: str, level: str, order_url: str) -> list[str]:
    collections = c.get(f"{url}/collections").json()
    if level == "collections":
        return [col["id"] for col in collections]
    if level == "chapters":
        collection_id = order_url.split("/collections/")[1].split("/")[0]
        col = next(col for col in collections if col["id"] == collection_id)
        return [ch["id"] for ch in col["chapters"]]
    chapter_id = order_url.split("/chapters/")[1].split("/")[0]
    chapters = [ch for col in collections for ch in col["chapters"]]
    ids: list[str] = next(ch["photoIds"] for ch in chapters if ch["id"] == chapter_id)
    return ids


@pytest.mark.parametrize("level", ["collections", "chapters", "photos"])
def test_reorder_works(
    admin_client: TestClient, admin_url: str, storage: FakeStorage, level: str
) -> None:
    order_url, ids = build_for_reorder(admin_client, admin_url, storage, level)
    assert admin_client.put(order_url, json={"ids": ids[::-1]}).status_code == 204
    assert current_ids(admin_client, admin_url, level, order_url) == ids[::-1]


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown"])
@pytest.mark.parametrize("level", ["collections", "chapters", "photos"])
def test_reorder_rejects_bad_id_sets_atomically(
    admin_client: TestClient, admin_url: str, storage: FakeStorage, level: str, mutation: str
) -> None:
    order_url, ids = build_for_reorder(admin_client, admin_url, storage, level)
    bad = {
        "missing": ids[::-1][:2],
        "duplicate": [ids[2], ids[2], ids[0]],
        "unknown": [ids[2], ids[1], "f" * 32],
    }[mutation]
    assert admin_client.put(order_url, json={"ids": bad}).status_code == 422
    assert current_ids(admin_client, admin_url, level, order_url) == ids


def test_covers_must_belong_to_collection(
    admin_client: TestClient, admin_url: str, storage: FakeStorage
) -> None:
    col = add_collection(admin_client, admin_url, "goa")
    ch = add_chapter(admin_client, admin_url, col["id"])
    inside, outside = (add_photo(admin_client, storage, admin_url)["id"] for _ in range(2))
    assign(admin_client, admin_url, ch["id"], [inside])
    url = f"{admin_url}/collections/{col['id']}/covers"
    assert admin_client.put(url, json={"photoIds": [outside]}).status_code == 422
    resp = admin_client.put(url, json={"photoIds": [inside]})
    assert resp.status_code == 200
    assert resp.json()["coverPhotoIds"] == [inside]


def test_moving_photo_out_of_collection_drops_it_from_covers(
    admin_client: TestClient, admin_url: str, storage: FakeStorage
) -> None:
    c1 = add_collection(admin_client, admin_url, "one")
    c2 = add_collection(admin_client, admin_url, "two")
    ch1 = add_chapter(admin_client, admin_url, c1["id"])
    ch2 = add_chapter(admin_client, admin_url, c2["id"])
    photo = add_photo(admin_client, storage, admin_url)["id"]
    assign(admin_client, admin_url, ch1["id"], [photo])
    admin_client.put(f"{admin_url}/collections/{c1['id']}/covers", json={"photoIds": [photo]})
    assign(admin_client, admin_url, ch2["id"], [photo])
    assert get_collection(admin_client, admin_url, c1["id"])["coverPhotoIds"] == []


def test_delete_chapter_unassigns_photos(
    admin_client: TestClient, admin_url: str, storage: FakeStorage
) -> None:
    col = add_collection(admin_client, admin_url, "goa")
    ch = add_chapter(admin_client, admin_url, col["id"])
    photo = add_photo(admin_client, storage, admin_url)["id"]
    assign(admin_client, admin_url, ch["id"], [photo])
    admin_client.put(f"{admin_url}/collections/{col['id']}/covers", json={"photoIds": [photo]})

    assert admin_client.delete(f"{admin_url}/chapters/{ch['id']}").status_code == 204

    photos = admin_client.get(f"{admin_url}/photos").json()
    assert [(p["id"], p["chapterId"]) for p in photos] == [(photo, None)]
    assert get_collection(admin_client, admin_url, col["id"])["coverPhotoIds"] == []


def test_delete_collection_keeps_photos(
    admin_client: TestClient, admin_url: str, storage: FakeStorage
) -> None:
    col = add_collection(admin_client, admin_url, "goa")
    ch = add_chapter(admin_client, admin_url, col["id"])
    photo = add_photo(admin_client, storage, admin_url)["id"]
    assign(admin_client, admin_url, ch["id"], [photo])

    assert admin_client.delete(f"{admin_url}/collections/{col['id']}").status_code == 204

    assert admin_client.get(f"{admin_url}/collections").json() == []
    assert [p["chapterId"] for p in admin_client.get(f"{admin_url}/photos").json()] == [None]


def test_unknown_ids_are_404(admin_client: TestClient, admin_url: str) -> None:
    missing = "f" * 32
    resp = admin_client.get(f"{admin_url}/collections/{missing}")
    assert (resp.status_code, resp.json()["detail"]) == (404, "collection not found")
    resp = admin_client.patch(f"{admin_url}/chapters/{missing}", json={})
    assert (resp.status_code, resp.json()["detail"]) == (404, "chapter not found")
    assert assign(admin_client, admin_url, missing, []).json()["detail"] == "chapter not found"


def test_mutations_are_audited(admin_client: TestClient, admin_url: str, db: Session) -> None:
    col = add_collection(admin_client, admin_url, "goa")
    admin_client.post(f"{admin_url}/collections/{col['id']}/publish")
    actions = [r.action for r in db.scalars(select(AuditLog).order_by(AuditLog.id))]
    assert {"collection.create", "collection.publish"} <= set(actions)


def test_all_routes_require_admin(client: TestClient, admin_url: str) -> None:
    client.headers["X-CSRF"] = "1"
    x = "f" * 32
    calls = [
        ("GET", f"{admin_url}/collections"),
        ("POST", f"{admin_url}/collections"),
        ("PUT", f"{admin_url}/collections/order"),
        ("GET", f"{admin_url}/collections/{x}"),
        ("PATCH", f"{admin_url}/collections/{x}"),
        ("DELETE", f"{admin_url}/collections/{x}"),
        ("POST", f"{admin_url}/collections/{x}/publish"),
        ("POST", f"{admin_url}/collections/{x}/unpublish"),
        ("PUT", f"{admin_url}/collections/{x}/covers"),
        ("POST", f"{admin_url}/collections/{x}/chapters"),
        ("PUT", f"{admin_url}/collections/{x}/chapters/order"),
        ("PATCH", f"{admin_url}/chapters/{x}"),
        ("DELETE", f"{admin_url}/chapters/{x}"),
        ("POST", f"{admin_url}/chapters/{x}/photos"),
        ("DELETE", f"{admin_url}/chapters/{x}/photos/{x}"),
        ("PUT", f"{admin_url}/chapters/{x}/photos/order"),
    ]
    for method, url in calls:
        assert client.request(method, url, json={}).status_code == 401, (method, url)
