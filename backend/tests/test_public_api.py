from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from tests.api_helpers import (
    add_chapter,
    add_collection,
    add_photo,
    add_published_photo,
    put_in_chapter,
)
from tests.fakes import FakeStorage
from tests.images import make_jpeg, rich_exif


@pytest.fixture
def seeded(admin_client: TestClient, admin_url: str, storage: FakeStorage) -> dict[str, Any]:
    """One published collection with two chapters, plus a standalone photo and a draft."""
    c = admin_client
    col = add_collection(c, admin_url, "goa", title="Goa", place="India", year="2024", intro="Hi")
    ch1 = add_chapter(c, admin_url, col["id"], title="Arrival", note="Rain")
    ch2 = add_chapter(c, admin_url, col["id"], title="Beaches", note="Sun")
    p1 = add_published_photo(c, storage, admin_url, "p1")
    p2 = add_published_photo(c, storage, admin_url, "p2")
    p3 = add_published_photo(c, storage, admin_url, "p3")
    draft = add_photo(c, storage, admin_url)  # stays a draft
    put_in_chapter(c, admin_url, ch1["id"], [p2["id"], p1["id"]])
    put_in_chapter(c, admin_url, ch2["id"], [draft["id"], p3["id"]])
    c.put(f"{admin_url}/collections/{col['id']}/covers", json={"photoIds": [p3["id"], draft["id"]]})
    c.post(f"{admin_url}/collections/{col['id']}/publish")
    standalone = add_published_photo(c, storage, admin_url, "standalone")
    c.cookies.clear()  # everything below is the anonymous public
    return {"col": col, "p1": p1, "p2": p2, "p3": p3, "draft": draft, "standalone": standalone}


def test_only_published_photos_listed_in_global_order(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    titles = [p["title"] for p in client.get("/photos").json()]
    assert titles == ["p1", "p2", "p3", "standalone"]


def test_public_endpoints_need_no_login_or_csrf_header(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    client.headers.pop("X-CSRF", None)
    assert client.get("/photos").status_code == 200
    assert client.get("/collections").status_code == 200


def test_photo_shape_matches_what_the_frontend_needs(
    admin_client: TestClient, admin_url: str, storage: FakeStorage
) -> None:
    add_published_photo(
        admin_client, storage, admin_url, "rich", data=make_jpeg((3000, 2000), exif=rich_exif())
    )
    admin_client.cookies.clear()
    photo = admin_client.get("/photos").json()[0]
    assert photo["aspectRatio"] == 1.5
    assert photo["exif"] == {
        "camera": "Sony ZV-E10",
        "focalLength": 38.0,
        "aperture": 3.6,
        "shutter": "1/250",
        "iso": 640,
    }
    assert set(photo["variants"]) == {"800", "1600", "2400"}
    assert photo["variants"]["1600"].startswith("https://cdn.test/photos/")
    assert photo["allowDownload"] is False
    assert photo["downloadUrl"] is None


def test_collection_detail_has_chapters_in_order_with_published_photos_only(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    body = client.get("/collections/goa").json()
    assert (body["title"], body["place"], body["year"], body["intro"]) == (
        "Goa",
        "India",
        "2024",
        "Hi",
    )
    chapters = [
        (ch["title"], ch["note"], [p["title"] for p in ch["photos"]]) for ch in body["chapters"]
    ]
    assert chapters == [("Arrival", "Rain", ["p2", "p1"]), ("Beaches", "Sun", ["p3"])]
    assert [p["title"] for p in body["photos"]] == ["p2", "p1", "p3"]


def test_draft_photo_hidden_inside_published_collection(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    body = client.get("/collections/goa").json()
    everything = str(body)
    assert seeded["draft"]["id"] not in everything
    assert [p["title"] for p in body["covers"]] == ["p3"]


def test_empty_chapters_are_omitted(
    admin_client: TestClient, admin_url: str, storage: FakeStorage
) -> None:
    c = admin_client
    col = add_collection(c, admin_url, "empty-ch")
    only_draft = add_chapter(c, admin_url, col["id"], title="Nothing visible")
    draft = add_photo(c, storage, admin_url)
    put_in_chapter(c, admin_url, only_draft["id"], [draft["id"]])
    c.post(f"{admin_url}/collections/{col['id']}/publish")
    c.cookies.clear()
    assert c.get("/collections/empty-ch").json()["chapters"] == []


def test_draft_collection_returns_404_and_hides_its_photos(
    admin_client: TestClient, admin_url: str, storage: FakeStorage
) -> None:
    c = admin_client
    col = add_collection(c, admin_url, "secret")
    ch = add_chapter(c, admin_url, col["id"])
    photo = add_published_photo(c, storage, admin_url, "in-draft-collection")
    c.put(f"{admin_url}/photos/{photo['id']}/allow-download", json={"allow": True})
    put_in_chapter(c, admin_url, ch["id"], [photo["id"]])
    c.cookies.clear()

    assert c.get("/collections/secret").status_code == 404
    assert [x["slug"] for x in c.get("/collections").json()] == []
    assert c.get("/photos").json() == []
    assert c.get(f"/photos/{photo['id']}/download", follow_redirects=False).status_code == 404


def test_unknown_collection_is_404(client: TestClient) -> None:
    assert client.get("/collections/nope").status_code == 404


def test_collections_listing_has_covers(client: TestClient, seeded: dict[str, Any]) -> None:
    listing = client.get("/collections").json()
    assert [c["slug"] for c in listing] == ["goa"]
    assert [p["title"] for p in listing[0]["covers"]] == ["p3"]
    assert "chapters" not in listing[0]


def test_collections_are_in_admin_order(
    admin_client: TestClient, admin_url: str, storage: FakeStorage
) -> None:
    c = admin_client
    ids = [add_collection(c, admin_url, s)["id"] for s in ("a", "b", "c")]
    for cid in ids:
        c.post(f"{admin_url}/collections/{cid}/publish")
    c.put(f"{admin_url}/collections/order", json={"ids": [ids[2], ids[0], ids[1]]})
    c.cookies.clear()
    assert [x["slug"] for x in c.get("/collections").json()] == ["c", "a", "b"]


def test_download_redirects_to_presigned_url_when_allowed(
    admin_client: TestClient, admin_url: str, storage: FakeStorage
) -> None:
    c = admin_client
    photo = add_published_photo(c, storage, admin_url, "dl")
    c.put(f"{admin_url}/photos/{photo['id']}/allow-download", json={"allow": True})
    c.cookies.clear()

    public = c.get("/photos").json()[0]
    assert public["downloadUrl"] == f"/photos/{photo['id']}/download"

    resp = c.get(public["downloadUrl"], follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"].startswith(
        f"https://fake-r2/private/downloads/{photo['id']}.jpg?get"
    )
    assert resp.headers["cache-control"] == "no-store"


def test_download_404_when_flag_off(
    admin_client: TestClient, admin_url: str, storage: FakeStorage
) -> None:
    photo = add_published_photo(admin_client, storage, admin_url, "nodl")
    admin_client.cookies.clear()
    resp = admin_client.get(f"/photos/{photo['id']}/download", follow_redirects=False)
    assert resp.status_code == 404


def test_download_404_for_draft_photo_even_if_flag_on(
    admin_client: TestClient, admin_url: str, storage: FakeStorage
) -> None:
    photo = add_photo(admin_client, storage, admin_url)
    admin_client.put(f"{admin_url}/photos/{photo['id']}/allow-download", json={"allow": True})
    admin_client.cookies.clear()
    resp = admin_client.get(f"/photos/{photo['id']}/download", follow_redirects=False)
    assert resp.status_code == 404


def test_download_404_for_unknown_or_malformed_id(client: TestClient) -> None:
    assert client.get(f"/photos/{'f' * 32}/download", follow_redirects=False).status_code == 404
    assert client.get("/photos/not-an-id/download", follow_redirects=False).status_code in (
        404,
        422,
    )


def test_etag_and_304(client: TestClient, seeded: dict[str, Any]) -> None:
    first = client.get("/photos")
    etag = first.headers["etag"]
    assert first.headers["cache-control"].startswith("public, max-age=")
    again = client.get("/photos", headers={"If-None-Match": etag})
    assert again.status_code == 304
    assert again.content == b""
    assert again.headers["etag"] == etag


def test_etag_changes_when_content_changes(
    admin_client: TestClient, admin_url: str, storage: FakeStorage
) -> None:
    c = admin_client
    add_published_photo(c, storage, admin_url, "one")
    etag = c.get("/photos").headers["etag"]
    add_published_photo(c, storage, admin_url, "two")
    resp = c.get("/photos", headers={"If-None-Match": etag})
    assert resp.status_code == 200
    assert resp.headers["etag"] != etag


def test_no_original_key_or_private_url_in_any_response(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    bodies = [client.get(u).text for u in ("/photos", "/collections", "/collections/goa")]
    for text in bodies:
        assert "originals/" not in text
        assert "downloads/" not in text
        assert "fake-r2" not in text
        assert "sortPosition" not in text
        assert "status" not in text  # public payloads carry no draft/published flag


@pytest.fixture
def query_count(client: TestClient) -> Iterator[list[int]]:
    counter = [0]
    engine = client.app.state.engine  # type: ignore[attr-defined]

    def count(*_: object) -> None:
        counter[0] += 1

    event.listen(engine, "before_cursor_execute", count)
    yield counter
    event.remove(engine, "before_cursor_execute", count)


def test_collection_endpoints_do_not_query_per_row(
    admin_client: TestClient, admin_url: str, storage: FakeStorage, query_count: list[int]
) -> None:
    c = admin_client

    def build(n: int) -> None:
        for i in range(n):
            col = add_collection(c, admin_url, f"col-{n}-{i}")
            ch = add_chapter(c, admin_url, col["id"])
            photo = add_published_photo(c, storage, admin_url, f"p{n}-{i}", size=(200, 100))
            put_in_chapter(c, admin_url, ch["id"], [photo["id"]])
            c.post(f"{admin_url}/collections/{col['id']}/publish")

    def queries_for(path: str) -> int:
        query_count[0] = 0
        assert c.get(path).status_code == 200
        return query_count[0]

    build(1)
    few = (queries_for("/collections"), queries_for("/collections/col-1-0"))
    build(4)
    many = (queries_for("/collections"), queries_for("/collections/col-1-0"))
    assert many == few
