from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.storage import Bucket
from app.models import AuditLog
from tests.fakes import FakeStorage
from tests.support.api_helpers import add_photo as _add_photo
from tests.support.api_helpers import upload
from tests.support.images import make_jpeg


@pytest.fixture
def base(admin_url: str) -> str:
    return f"{admin_url}/photos"


def add_photo(c: TestClient, storage: FakeStorage, base: str) -> dict[str, Any]:
    return _add_photo(c, storage, base.removesuffix("/photos"))


def test_upload_flow_creates_variants_and_draft(
    admin_client: TestClient, storage: FakeStorage, base: str
) -> None:
    photo = add_photo(admin_client, storage, base)
    assert photo["status"] == "draft"
    assert set(photo["variants"]) == {"800", "1600", "2400"}
    assert photo["variants"]["800"].startswith("https://cdn.test/photos/")
    public_keys = {k for (b, k) in storage.objects if b is Bucket.PUBLIC}
    assert len(public_keys) == 3
    assert all(k.endswith(".webp") for k in public_keys)


def test_original_and_download_copy_only_in_private_bucket(
    admin_client: TestClient, storage: FakeStorage, base: str
) -> None:
    photo = add_photo(admin_client, storage, base)
    private = {k for (b, k) in storage.objects if b is Bucket.PRIVATE}
    assert private == {f"originals/{photo['id']}.jpg", f"downloads/{photo['id']}.jpg"}
    assert not any("original" in k for (b, k) in storage.objects if b is Bucket.PUBLIC)


def test_confirm_rejects_non_jpeg_and_cleans_up(
    admin_client: TestClient, storage: FakeStorage, base: str
) -> None:
    photo_id = upload(admin_client, storage, base, make_jpeg((100, 100), fmt="PNG"))
    assert admin_client.post(f"{base}/{photo_id}/confirm").status_code == 422
    assert storage.objects == {}
    assert admin_client.get(base).json() == []


def test_confirm_rejects_decompression_bomb(
    admin_client: TestClient, storage: FakeStorage, base: str
) -> None:
    admin_client.app.state.settings.max_image_pixels = 10_000  # type: ignore[attr-defined]
    photo_id = upload(admin_client, storage, base, make_jpeg((200, 200)))
    assert admin_client.post(f"{base}/{photo_id}/confirm").status_code == 422
    assert storage.objects == {}


def test_confirm_rejects_oversized_file_without_reading_it(
    admin_client: TestClient, storage: FakeStorage, base: str
) -> None:
    admin_client.app.state.settings.max_upload_bytes = 500  # type: ignore[attr-defined]
    photo_id = upload(admin_client, storage, base, make_jpeg((400, 400)))
    assert admin_client.post(f"{base}/{photo_id}/confirm").status_code == 422
    assert storage.objects == {}


def test_confirm_without_an_uploaded_file_is_404(admin_client: TestClient, base: str) -> None:
    ticket = admin_client.post(f"{base}/upload-url").json()
    assert admin_client.post(f"{base}/{ticket['photoId']}/confirm").status_code == 404


def test_confirm_rejects_malformed_ids(admin_client: TestClient, base: str) -> None:
    assert admin_client.post(f"{base}/..%2Fsecret/confirm").status_code in (404, 422)


def test_confirming_twice_does_not_duplicate(
    admin_client: TestClient, storage: FakeStorage, base: str
) -> None:
    photo = add_photo(admin_client, storage, base)
    assert admin_client.post(f"{base}/{photo['id']}/confirm").status_code == 409
    assert len(admin_client.get(base).json()) == 1


def test_allow_download_defaults_false_and_can_be_toggled(
    admin_client: TestClient, storage: FakeStorage, base: str
) -> None:
    photo = add_photo(admin_client, storage, base)
    assert photo["allowDownload"] is False
    resp = admin_client.put(f"{base}/{photo['id']}/allow-download", json={"allow": True})
    assert resp.json()["allowDownload"] is True


def test_publish_and_unpublish(admin_client: TestClient, storage: FakeStorage, base: str) -> None:
    photo = add_photo(admin_client, storage, base)
    assert admin_client.post(f"{base}/{photo['id']}/publish").json()["status"] == "published"
    assert admin_client.post(f"{base}/{photo['id']}/unpublish").json()["status"] == "draft"


def test_update_metadata(admin_client: TestClient, storage: FakeStorage, base: str) -> None:
    photo = add_photo(admin_client, storage, base)
    resp = admin_client.patch(
        f"{base}/{photo['id']}", json={"title": "Ghat at dusk", "place": "Ujjain"}
    )
    assert (resp.json()["title"], resp.json()["place"]) == ("Ghat at dusk", "Ujjain")


def test_delete_removes_all_objects(
    admin_client: TestClient, storage: FakeStorage, base: str
) -> None:
    photo = add_photo(admin_client, storage, base)
    assert admin_client.delete(f"{base}/{photo['id']}").status_code == 204
    assert storage.objects == {}
    assert admin_client.get(base).json() == []


def test_new_photos_are_appended_to_the_order(
    admin_client: TestClient, storage: FakeStorage, base: str
) -> None:
    first = add_photo(admin_client, storage, base)
    second = add_photo(admin_client, storage, base)
    assert [p["id"] for p in admin_client.get(base).json()] == [first["id"], second["id"]]


def test_reorder_changes_the_order(
    admin_client: TestClient, storage: FakeStorage, base: str
) -> None:
    ids = [add_photo(admin_client, storage, base)["id"] for _ in range(3)]
    assert admin_client.put(f"{base}/order", json={"ids": ids[::-1]}).status_code == 204
    assert [p["id"] for p in admin_client.get(base).json()] == ids[::-1]


@pytest.mark.parametrize("mutate", ["missing", "duplicate", "unknown"])
def test_reorder_rejects_bad_id_sets_without_partial_change(
    admin_client: TestClient, storage: FakeStorage, base: str, mutate: str
) -> None:
    ids = [add_photo(admin_client, storage, base)["id"] for _ in range(3)]
    bad = {
        "missing": ids[::-1][:2],
        "duplicate": [ids[2], ids[2], ids[0]],
        "unknown": [ids[2], ids[1], "nope"],
    }[mutate]
    assert admin_client.put(f"{base}/order", json={"ids": bad}).status_code == 422
    assert [p["id"] for p in admin_client.get(base).json()] == ids


def test_mutations_are_audited(
    admin_client: TestClient, storage: FakeStorage, base: str, db: Session
) -> None:
    photo = add_photo(admin_client, storage, base)
    admin_client.post(f"{base}/{photo['id']}/publish")
    actions = [r.action for r in db.scalars(select(AuditLog).order_by(AuditLog.id))]
    assert "photo.publish" in actions


def test_all_routes_require_admin(client: TestClient, base: str) -> None:
    client.headers["X-CSRF"] = "1"
    calls = [
        ("POST", f"{base}/upload-url"),
        ("POST", f"{base}/abc/confirm"),
        ("GET", base),
        ("PATCH", f"{base}/abc"),
        ("POST", f"{base}/abc/publish"),
        ("POST", f"{base}/abc/unpublish"),
        ("PUT", f"{base}/abc/allow-download"),
        ("DELETE", f"{base}/abc"),
        ("PUT", f"{base}/order"),
    ]
    for method, url in calls:
        assert client.request(method, url, json={}).status_code == 401, (method, url)


def test_patch_with_null_title_is_rejected_not_a_server_error(
    admin_client: TestClient, storage: FakeStorage, base: str
) -> None:
    photo = add_photo(admin_client, storage, base)
    resp = admin_client.patch(f"{base}/{photo['id']}", json={"title": None})
    assert resp.status_code == 422
    assert admin_client.get(base).json()[0]["title"] == ""


def test_patch_can_clear_place(admin_client: TestClient, storage: FakeStorage, base: str) -> None:
    photo = add_photo(admin_client, storage, base)
    admin_client.patch(f"{base}/{photo['id']}", json={"place": "Ujjain"})
    resp = admin_client.patch(f"{base}/{photo['id']}", json={"place": None})
    assert resp.status_code == 200
    assert resp.json()["place"] is None


def test_photo_edits_refuse_fields_they_do_not_own(
    admin_client: TestClient, storage: FakeStorage, base: str
) -> None:
    photo = add_photo(admin_client, storage, base)
    resp = admin_client.patch(f"{base}/{photo['id']}", json={"status": "published"})
    assert resp.status_code == 422
    assert admin_client.get(base).json()[0]["status"] == "draft"
