"""Rows become response models with `Model.model_validate(row)`: no per-entity mapping helpers.

Where a model needs something the row does not hold (the CDN address of an image), it arrives
through Pydantic's validation context.
"""

from app.models import Admin, Status
from app.schemas.auth import AdminOut
from app.schemas.collections import ChapterOut, CollectionOut
from app.schemas.photos import PhotoOut
from app.schemas.public import PublicCollectionSummary, PublicPhoto
from tests.support.builders import at, make_chapter, make_collection, make_photo, published

CDN = {"public_url": lambda key: f"https://cdn.test/{key}"}


def photo(**kw: object):  # type: ignore[no-untyped-def]
    values = {
        "created_at": at(1),
        "variant_keys": {"800": "photos/p1/800.webp", "1600": "photos/p1/1600.webp"},
        "exif": {"camera": "Sony", "focal_length": 38.0, "iso": 640},
        "status": Status.DRAFT,
        "allow_download": False,
        "sort_position": 3,
    }
    values.update(kw)
    return make_photo("p1", **values)


# -- photos -------------------------------------------------------------------------------


def test_an_admin_photo_is_built_from_the_row_and_gets_cdn_urls_from_the_context() -> None:
    out = PhotoOut.model_validate(photo(unsplash_id="u1", place="Ghat"), context=CDN)

    assert out.id == "p1" and out.place == "Ghat" and out.unsplash_id == "u1"
    assert out.status is Status.DRAFT and out.sort_position == 3
    assert out.variants == {
        "800": "https://cdn.test/photos/p1/800.webp",
        "1600": "https://cdn.test/photos/p1/1600.webp",
    }


def test_an_admin_photo_serialises_with_camel_case_names_and_never_the_storage_keys() -> None:
    body = PhotoOut.model_validate(photo(original_key="originals/p1.jpg"), context=CDN).model_dump(
        mode="json", by_alias=True
    )
    assert {"aspectRatio", "allowDownload", "sortPosition", "chapterId", "createdAt"} <= set(body)
    assert "originalKey" not in body and "originals/" not in str(body)


def test_a_public_photo_carries_its_download_route_only_when_downloads_are_allowed() -> None:
    off = PublicPhoto.model_validate(photo(), context=CDN)
    on = PublicPhoto.model_validate(photo(allow_download=True), context=CDN)
    assert (off.allow_download, off.download_url) == (False, None)
    assert (on.allow_download, on.download_url) == (True, "/photos/p1/download")


def test_a_public_photo_exposes_exif_in_camel_case_and_no_internal_fields() -> None:
    body = PublicPhoto.model_validate(photo(), context=CDN).model_dump(
        mode="json", by_alias=True, exclude_none=True
    )
    assert body["exif"] == {"camera": "Sony", "focalLength": 38.0, "iso": 640}
    assert body["variants"]["800"] == "https://cdn.test/photos/p1/800.webp"
    assert not ({"status", "sortPosition", "chapterId", "downloadKey", "originalKey"} & set(body))


# -- chapters and collections -------------------------------------------------------------


def test_a_chapter_lists_its_photo_ids_in_the_order_its_relationship_holds_them() -> None:
    chapter = make_chapter("ch1", "c1", title="Arrival", note="Rain", position=2)
    chapter.photos = [make_photo("b"), make_photo("a")]

    out = ChapterOut.model_validate(chapter)

    assert (out.id, out.collection_id, out.title, out.note, out.position) == (
        "ch1",
        "c1",
        "Arrival",
        "Rain",
        2,
    )
    assert out.photo_ids == ["b", "a"]


def test_a_collection_is_built_with_its_chapters_and_their_photo_ids_in_one_call() -> None:
    collection = make_collection("c1", slug="goa", title="Goa", year="2024", cover_photo_ids=["a"])
    first, second = make_chapter("ch1", "c1"), make_chapter("ch2", "c1", position=1)
    first.photos = [make_photo("a")]
    collection.chapters = [first, second]

    out = CollectionOut.model_validate(collection)

    assert (out.slug, out.title, out.year, out.cover_photo_ids) == ("goa", "Goa", "2024", ["a"])
    assert [(c.id, c.photo_ids) for c in out.chapters] == [("ch1", ["a"]), ("ch2", [])]
    body = out.model_dump(mode="json", by_alias=True)
    assert {"coverPhotoIds", "sortPosition"} <= set(body)
    assert body["chapters"][0]["photoIds"] == ["a"]


def test_a_collection_without_chapters_has_an_empty_list() -> None:
    assert CollectionOut.model_validate(make_collection("c1")).chapters == []


def test_the_public_collection_summary_reads_only_the_public_fields_from_the_row() -> None:
    row = make_collection(
        "c1", slug="goa", title="Goa", place="India", year="2024", intro="Rain", **published()
    )
    out = PublicCollectionSummary.model_validate(row, context=CDN)
    assert (out.slug, out.title, out.place, out.year, out.intro, out.covers) == (
        "goa",
        "Goa",
        "India",
        "2024",
        "Rain",
        [],
    )
    body = out.model_dump(mode="json", by_alias=True)
    assert not ({"id", "status", "sortPosition", "coverPhotoIds"} & set(body))


# -- admin identity -----------------------------------------------------------------------


def test_the_signed_in_admin_exposes_only_the_username() -> None:
    row = Admin(username="nitish", password_hash="h", totp_secret="s", recovery_code_hashes=[])
    assert AdminOut.model_validate(row).model_dump() == {"username": "nitish"}
